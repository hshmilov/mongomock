#!/bin/bash

if [ ${SSH_443_DISABLED} == "TRUE" ]; then
    echo "SSH_443 is disabled"
    exit 0
fi

echo "=> Setting up the reverse ssh on 443 - ${PUBLIC_SSH_HOST_USER}@${PUBLIC_SSH_HOST_ADDR}"
while true
do
    sshpass -p ${PUBLIC_SSH_HOST_PASSW} ssh -oServerAliveInterval=30 -oServerAliveCountMax=3 -oStrictHostKeyChecking=no -NTR 0:localhost:22 ${PUBLIC_SSH_HOST_USER}@${PUBLIC_SSH_HOST_ADDR} -p 443
    echo "=> Tunnel Link down!"
    echo "=> Wait 15 seconds to reconnect"
    sleep 15
    echo "=> Reconnecting..."
done