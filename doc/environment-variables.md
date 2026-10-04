# PyNTS - Environment Variables

Below all the available environment variables will be described

## NETWORK_FUNCTION_TYPE
- should be automatically set by the Dockerfile to a specific network function that the image implements


## NETCONF_USERNAME
- type string
- NETCONF and SFTP username. SFTP configures this system account at container startup.
- SFTP accepts only the configured account. The existing FTP account remains `netconf`; changing the SFTP username does not change the FTP allow-list.
- The SFTP username starts with a lowercase letter, uses lowercase letters, digits, `_` or `-`, and is at most 32 characters. Apart from the existing `netconf` account, existing accounts must have a regular UID in the range 1000–65533.

## NETCONF_PASSWORD
- type string
- NETCONF and SFTP password. SFTP applies this password at container startup; empty values and line breaks are rejected.
- FTP still authenticates the `netconf` system account. When `NETCONF_USERNAME` is changed, its build-time password `netconf!` remains valid for FTP; `NETCONF_PASSWORD` applies to the configured NETCONF/SFTP account. When the username remains `netconf`, the startup password update also changes that shared FTP account password.

## SDNR_RESTCONF_URL
- type string
- URL for the RESTCONF interface of the SDN controller
- example: http://controller.dcn.smo.o-ran-sc.org

## SDNR_USERNAME
- type string
- SDNR credentials

## SDNR_PASSWORD
- type string
- SDNR credentials

## VES_URL
- type string
- URL of VES collector
- example: https://10.20.35.128:8443/eventListener/v7

## VES_USERNAME
- type string
- VES collector credentials

## VES_PASSWORD
- type string
- VES collector credentials

## NETWORK_INTERFACE
- type string
- the name of the network interface which can be used by the simulator. Is only relevant when docker image is ran in network_mode="host" (in this case, it needs to point to an interface name from the host system).

## O_DU_CALLHOME_PORT
- type string
- the port number where a simulated O-DU listens for call-home connections. Is only relevant when docker image is ran in network_mode="host"
- default value is **4335**

## SDNR_CERTIFICATE_MARKERS
- type bool
- if **True**, the *add-trusted-certificate* operation from the simulated O-RU going towards the SDN Controller will contain the *"--- BEGIN ---"* and *"--- END ---"* markers of a certificate, when sending it to ODL. If **False**, the markers will not be part of the certificate. The markers are needed starting with ODL Scandium version. Only relevant for NETCONF Call Home (implemented in O-RU currently).
- default value is **False**
