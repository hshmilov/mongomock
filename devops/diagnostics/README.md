please add a README.md file to devops/diagnostics:

# Diagnostics Service
A container that diagnostic connection from clients to Axonius RnD for support and diagnostics.

## How to use
change the host and password of the diagnostics server in `diag_env.json` and then run `./axonius.sh service diagnostics up`

## Technical Explanation
The container's docker network is 'host' which means that the container's network stack is not isolated from the Docker host. This means that a script that tunnels communication to port 22 actually tunnels it to the sshd of the host.