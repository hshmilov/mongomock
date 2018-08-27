#!/bin/bash

cat > ./stunnel_autogen.conf << EOF
debug = info
output = /dev/stdout
pid = /var/run/stunnel.pid

[ssh]
client = yes
accept = 127.0.0.1:${LOCAL_STUNNEL_LINK_PORT}
EOF

# if there is proxy data - set it in conf
if [[ -n "${PROXY_CONNECT}" ]]; then

    cat >> ./stunnel_autogen.conf << EOF
protocolHost = ${PUBLIC_SSL_HOST_ADDR}:443
protocol = connect
connect = ${PROXY_CONNECT}
protocolPassword = ${PROXY_PASSWORD}
protocolUsername = ${PROXY_USERNAME}
EOF

else

cat >> ./stunnel_autogen.conf << EOF
    connect = ${PUBLIC_SSL_HOST_ADDR}:443
EOF

fi

echo "=> Setting up the reverse ssh over stunnel - ${PUBLIC_SSL_HOST_USER}@${PUBLIC_SSL_HOST_ADDR}"
while true
do
    pkill stunnel
    stunnel4 ./stunnel_autogen.conf
    sleep 5
    sshpass -p ${PUBLIC_SSL_HOST_PASSW} ssh -oServerAliveInterval=30 -oServerAliveCountMax=3 -oStrictHostKeyChecking=no -NTR ${PUBLIC_SSL_HOST_STUNNEL_LINK_PORT}:localhost:22 ${PUBLIC_SSL_HOST_USER}@localhost -p ${LOCAL_STUNNEL_LINK_PORT}
    echo "=> Tunnel Link down!, waiting to reconnect"
    sleep 10
    echo "=> Reconnecting..."
done
