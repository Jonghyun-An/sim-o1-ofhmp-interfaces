# SPDX-License-Identifier: Apache-2.0
"""Run against an isolated PyNTS SFTP test container, never a production server."""
import io
import os
import uuid

import paramiko
import pytest


@pytest.fixture
def endpoint():
    host = os.environ.get("PYNTS_SFTP_TEST_HOST")
    if not host:
        pytest.skip("set PYNTS_SFTP_TEST_HOST for the isolated SFTP fixture")
    return (host, int(os.environ["PYNTS_SFTP_TEST_PORT"]),
            os.environ.get("NETCONF_USERNAME", "netconf"),
            os.environ.get("NETCONF_PASSWORD", "netconf!"))


def connect(endpoint, username=None, password=None):
    host, port, configured_user, configured_password = endpoint
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, port=port, username=username or configured_user,
                       password=configured_password if password is None else password,
                       allow_agent=False, look_for_keys=False, timeout=5,
                       auth_timeout=5, banner_timeout=5)
    except Exception:
        client.close()
        raise
    return client


def test_configured_credentials_transfer_pm_file(endpoint):
    with connect(endpoint) as client, client.open_sftp() as sftp:
        assert sftp.normalize(".") == "/ftp"
        path = "/ftp/credential-test-%s.txt" % uuid.uuid4().hex
        expected = b"PM data round trip\n"
        try:
            sftp.putfo(io.BytesIO(expected), path)
            with sftp.open(path, "rb") as remote:
                assert remote.read() == expected
        finally:
            try:
                sftp.remove(path)
            except OSError:
                pass


def test_wrong_password_is_rejected(endpoint):
    with pytest.raises(paramiko.AuthenticationException):
        connect(endpoint, password="deliberately-incorrect-password")


def test_old_default_credentials_are_rejected_after_override(endpoint):
    if endpoint[2:] == ("netconf", "netconf!"):
        pytest.skip("default credentials are intentionally configured")
    with pytest.raises(paramiko.AuthenticationException):
        connect(endpoint, username="netconf", password="netconf!")
