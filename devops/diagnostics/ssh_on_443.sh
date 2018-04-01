#!/bin/bash

# these default values are making a lot of sense
PUBLIC_HOST_PORT=443
PROXY_PORT=22
REMOTE_HOST_BIND_PORT=0

if [ ${SSH_443_DISABLED} == "TRUE" ]; then
    echo "SSH_443 is disabled"
    exit 0
fi

echo "=> Setting up the reverse ssh on 443 - ${PUBLIC_SSH_HOST_USER}@${PUBLIC_SSH_HOST_ADDR}"
while true
do
    sshpass -p ${PUBLIC_SSH_HOST_PASSW} ssh -oStrictHostKeyChecking=no -NTR ${REMOTE_HOST_BIND_PORT}:localhost:${PROXY_PORT} ${PUBLIC_SSH_HOST_USER}@${PUBLIC_SSH_HOST_ADDR} -p ${PUBLIC_HOST_PORT}
    echo "=> Tunnel Link down!"
    echo "=> Wait 15 seconds to reconnect"
    sleep 15
    echo "=> Reconnecting..."
done
