#!/bin/bash

# these default values are making a lot of sense
PUBLIC_HOST_PORT=443
PROXY_PORT=22
REMOTE_HOST_BIND_PORT=0
PUBLIC_HOST_USER=ubuntu


echo "=> Connecting to Remote SSH server ${PUBLIC_HOST_ADDR}:${PUBLIC_HOST_PORT}"
echo "${PUBLIC_HOST_PORT}, ${PROXY_PORT}, ${REMOTE_HOST_BIND_PORT}"

KNOWN_HOSTS="/root/.ssh/known_hosts"

echo "=> Scanning and save fingerprint from the remote server ..."
ssh-keyscan -p ${PUBLIC_HOST_PORT} -H ${PUBLIC_HOST_ADDR} > ${KNOWN_HOSTS}
if [ $(stat -c %s ${KNOWN_HOSTS}) == "0" ]; then
    echo "=> cannot get fingerprint from remote server, exiting ...;"
    exit 1
fi

echo "====REMOTE FINGERPRINT===="
cat ${KNOWN_HOSTS}
echo "====REMOTE FINGERPRINT===="

echo "Added key"

echo "=> Setting up the reverse ssh tunnel"
while true
do
    sshpass -p ${PUBLIC_HOST_PASSW} ssh -NTR ${REMOTE_HOST_BIND_PORT}:localhost:${PROXY_PORT} ${PUBLIC_HOST_USER}@${PUBLIC_HOST_ADDR} -p ${PUBLIC_HOST_PORT}
    echo "=> Tunnel Link down!"
    echo "=> Wait 15 seconds to reconnect"
    sleep 15
    echo "=> Reconnecting..."
done
