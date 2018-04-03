#!/bin/bash

if [ ${STUNNEL_DISABLED} == "TRUE" ]; then
    echo "STUNNEL is disabled"
    exit 0
fi

cat > ./stunnel_autogen.conf << EOF
debug = info
output = /var/log/stunnel.log
pid = /var/run/stunnel.pid

[ssh]
client = yes
accept = 127.0.0.1:0
connect = ${PUBLIC_SSL_HOST_ADDR}:443

EOF

echo "=> Setting up the reverse ssh over stunnel - ${PUBLIC_SSL_HOST_USER}@${PUBLIC_SSL_HOST_ADDR}"
while true
do
    pkill stunnel4
    stunnel4 ./stunnel_autogen.conf

    STUNNEL_LISTEN_PORT=$(netstat -netapee | grep stunnel4 | awk '{print $4}' | cut -d: -f2)
    sed -i "s/STUNNEL_LISTEN_PORT=.*/STUNNEL_LISTEN_PORT=${STUNNEL_LISTEN_PORT}/g" env_autogen.sh

    sshpass -p ${PUBLIC_SSL_HOST_PASSW} autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -oStrictHostKeyChecking=no -NTR 0:localhost:22 ${PUBLIC_SSL_HOST_USER}@localhost -p ${STUNNEL_LISTEN_PORT}
    echo "=> Tunnel Link down!"
    echo "=> Wait 15 seconds to reconnect"
    sleep 15
    echo "=> Reconnecting..."
done