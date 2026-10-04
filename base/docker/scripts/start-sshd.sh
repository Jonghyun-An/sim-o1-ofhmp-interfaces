#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
set -eu

username=${NETCONF_USERNAME-netconf}
password=${NETCONF_PASSWORD-netconf!}
case "$username" in
    ""|[!a-z]*|*[!a-z0-9_-]*)
        echo "NETCONF_USERNAME is not a valid system username" >&2
        exit 2
        ;;
esac
if [ "${#username}" -gt 32 ]; then
    echo "NETCONF_USERNAME must be at most 32 characters" >&2
    exit 2
fi
carriage_return=$(printf '\r')
case "$password" in
    ""|*'
'*|*"$carriage_return"*)
        echo "NETCONF_PASSWORD must be non-empty and contain no line breaks" >&2
        exit 2
        ;;
esac

if id "$username" >/dev/null 2>&1; then
    uid=$(id -u "$username")
    if [ "$uid" -eq 0 ] || [ "$uid" -ge 65534 ] || { [ "$uid" -lt 1000 ] && [ "$username" != netconf ]; }; then
        echo "NETCONF_USERNAME must not select a reserved system account" >&2
        exit 2
    fi
else
    adduser --disabled-password --gecos "" --no-create-home \
        --shell /usr/sbin/nologin --ingroup netconf "$username"
fi
printf '%s:%s\n' "$username" "$password" | chpasswd
# Preserve the existing FTP account and grant the SFTP account shared access.
usermod -a -G netconf "$username"
chown netconf:netconf /ftp
chmod g+w /ftp

# Keep the Match block after the global SSH settings, including Includes.
config=/run/sshd/pynts-sftp.conf
cat /etc/ssh/sshd_config > "$config"
printf '\nAllowUsers %s\nMatch User %s\n    ChrootDirectory /\n    X11Forwarding no\n    AllowTcpForwarding no\n    ForceCommand internal-sftp -d /ftp\n' "$username" "$username" >> "$config"
exec /usr/sbin/sshd -D -f "$config" "$@"
