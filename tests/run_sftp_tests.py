#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run identical SFTP regressions against Docker fragments from --source."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET


def wait_ssh(port):
    for _ in range(100):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3) as sock:
                if sock.recv(64).startswith(b"SSH-"):
                    return
        except OSError:
            pass
        time.sleep(0.1)
    raise RuntimeError("SSH fixture did not become ready")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    patched = (source / "base/docker/scripts/start-sshd.sh").exists()
    dockerfile = (source / "base/Dockerfile").read_text()
    blocks = dockerfile[dockerfile.index("# add netconf user"):dockerfile.index("# use /opt/dev")]
    install = "COPY ./base/docker/scripts /opt/dev/scripts"
    if install not in dockerfile.splitlines():
        raise RuntimeError("production Dockerfile does not install the supervisor script path")
    tag = "oran-sftp-regression:" + uuid.uuid4().hex[:12]
    summary = {"source": str(source), "patched": patched, "variants": [], "validation": []}
    with tempfile.TemporaryDirectory(prefix="oran-sftp-") as directory:
        context = Path(directory)
        shutil.copytree(source / "base/docker/scripts", context / "base/docker/scripts")
        (context / "base/docker/conf").mkdir(parents=True)
        for name in ["vsftpd.conf", "vsftpd.userlist"]:
            shutil.copy2(source / "base/docker/conf" / name, context / "base/docker/conf" / name)
        fixture = "FROM ubuntu:22.04\nRUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-server && rm -rf /var/lib/apt/lists/*\n" + blocks + install + '\nCMD ["sleep", "infinity"]\n'
        (context / "Dockerfile").write_text(fixture)
        (output / "fixture-Dockerfile").write_text(fixture)
        try:
            with (output / "build.log").open("w") as log:
                subprocess.run(["docker", "build", "--progress=plain", "-t", tag, str(context)], check=True, stdout=log, stderr=subprocess.STDOUT)
            for label, settings in [
                ("default", {}), ("username", {"NETCONF_USERNAME": "oranuser"}),
                ("password", {"NETCONF_PASSWORD": "example-new-password"}),
                ("both", {"NETCONF_USERNAME": "oranuser", "NETCONF_PASSWORD": "example-new-password"}),
                ("special", {"NETCONF_USERNAME": "oranuser", "NETCONF_PASSWORD": "example:pass$word%!'"}),
            ]:
                container = "oran-sftp-" + uuid.uuid4().hex[:12]
                try:
                    command = ["docker", "run", "-d", "--name", container, "-p", "127.0.0.1::22"]
                    for key in settings:
                        command += ["-e", key]
                    subprocess.run(command + [tag], env={**os.environ, **settings}, check=True, stdout=subprocess.PIPE)
                    port = int(subprocess.check_output(["docker", "port", container, "22/tcp"], text=True).strip().rsplit(":", 1)[1])
                    daemon = ["/bin/sh", "/opt/dev/scripts/start-sshd.sh", "-e"] if patched else ["/usr/sbin/sshd", "-D", "-e"]
                    subprocess.run(["docker", "exec", "-d", container, *daemon], check=True)
                    wait_ssh(port)
                    testenv = {**os.environ, "PYNTS_SFTP_TEST_HOST": "127.0.0.1", "PYNTS_SFTP_TEST_PORT": str(port), "NETCONF_USERNAME": settings.get("NETCONF_USERNAME", "netconf"), "NETCONF_PASSWORD": settings.get("NETCONF_PASSWORD", "netconf!")}
                    with (output / (label + ".log")).open("w") as log:
                        result = subprocess.run([sys.executable, "-m", "pytest", "-q", str(Path(__file__).with_name("test_sftp_credentials.py")), "--junitxml=" + str(output / (label + ".xml"))], env=testenv, stdout=log, stderr=subprocess.STDOUT)
                    cases = ET.parse(output / (label + ".xml")).getroot().findall(".//testcase")
                    counts = {"total": len(cases), "failed": sum(t.find("failure") is not None for t in cases), "errors": sum(t.find("error") is not None for t in cases), "skipped": sum(t.find("skipped") is not None for t in cases)}
                    counts["passed"] = counts["total"] - counts["failed"] - counts["errors"] - counts["skipped"]
                    summary["variants"].append({"name": label, "exit_code": result.returncode, "counts": counts})
                    print(label, counts, flush=True)
                finally:
                    subprocess.run(["docker", "rm", "-f", container], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if patched:
                for label, settings in [
                    ("empty-user", {"NETCONF_USERNAME": ""}), ("leading-hyphen", {"NETCONF_USERNAME": "-user"}),
                    ("invalid-user", {"NETCONF_USERNAME": "bad user"}), ("uppercase-user", {"NETCONF_USERNAME": "OranUser"}),
                    ("root-user", {"NETCONF_USERNAME": "root"}), ("system-user", {"NETCONF_USERNAME": "daemon"}),
                    ("nobody-user", {"NETCONF_USERNAME": "nobody"}), ("long-user", {"NETCONF_USERNAME": "a" * 33}),
                    ("digit-user", {"NETCONF_USERNAME": "1oranuser"}),
                    ("empty-password", {"NETCONF_PASSWORD": ""}), ("newline-password", {"NETCONF_PASSWORD": "bad\nline"}),
                    ("carriage-password", {"NETCONF_PASSWORD": "bad\rline"}),
                ]:
                    command = ["docker", "run", "--rm"]
                    for key in settings:
                        command += ["-e", key]
                    with (output / ("invalid-" + label + ".log")).open("w") as log:
                        result = subprocess.run(command + [tag, "/bin/sh", "/opt/dev/scripts/start-sshd.sh"], env={**os.environ, **settings}, stdout=log, stderr=subprocess.STDOUT)
                    summary["validation"].append({"name": label, "exit_code": result.returncode, "passed": result.returncode == 2})
        finally:
            subprocess.run(["docker", "image", "rm", tag], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (output / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
    return int(any(v["exit_code"] for v in summary["variants"]) or any(not v["passed"] for v in summary["validation"]))


if __name__ == "__main__":
    sys.exit(main())
