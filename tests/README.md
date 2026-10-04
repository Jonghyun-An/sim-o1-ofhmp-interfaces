# SFTP credential regression

Run against an isolated container's forwarded SFTP port:

```sh
python3 -m pip install -r tests/requirements.txt
export PYNTS_SFTP_TEST_HOST=127.0.0.1
export PYNTS_SFTP_TEST_PORT=2222
# Set NETCONF_USERNAME and NETCONF_PASSWORD to the fixture's configured values.
python3 -m pytest -q tests/test_sftp_credentials.py
```

The tests upload and read back a temporary PM file, reject a wrong password,
and reject the old defaults after a credential override. No NETCONF or VES
session is exercised by this SFTP test.

To build an isolated Ubuntu 22.04 fixture using the account, SSH configuration
and scripts COPY instructions from a selected source revision, run:

```sh
python3 tests/run_sftp_tests.py --output /tmp/pynts-sftp-after
python3 tests/run_sftp_tests.py --source /path/to/unpatched/checkout --output /tmp/pynts-sftp-before
```

Run both commands from the patched checkout, so they use the identical tests.
Docker and network access for the base image are required. The second command
is expected to fail credential-override regressions on the unpatched source.
Raw logs, JUnit reports and the fixture Dockerfile are saved under `--output`.
This fixture does not build libyang, sysrepo or the full PyNTS application.
