DEFAULT_OPENVPN_CONFIG = '''mode p2p
server 192.167.255.0 255.255.255.0 # your openvpn subnet avoid clash with customer and docker networks
verb 4 # verbosity
key /etc/openvpn/pki/private/server.key
ca /etc/openvpn/pki/ca.crt
cert /etc/openvpn/pki/issued/server.crt
dh /etc/openvpn/pki/dh.pem
tls-auth /etc/openvpn/pki/ta.key
local 0.0.0.0
key-direction 0
keepalive 10 60
persist-key
persist-tun
proto tcp
port 2212
dev tun0 # layer3 link
topology subnet
status /tmp/openvpn-status.log
user nobody
group nogroup'''

base_config = '''#!/bin/sh
AXONIUS_AGENT_BASE_FOLDER=/opt/axonius
mkdir $AXONIUS_AGENT_BASE_FOLDER
cd $AXONIUS_AGENT_BASE_FOLDER
cat <<EOF > Dockerfile
FROM alpine:3.11.6

RUN apk add --no-cache openvpn curl bind-tools vim alpine-sdk linux-headers curl iptables iptables-dev iptables tcptraceroute bash dnsmasq

RUN mkdir /conf
RUN mkdir /resolv

RUN mkdir /scripts
COPY scripts/* /scripts/
RUN chmod +x /scripts/*.sh

CMD ["/scripts/init.sh"]
EOF

mkdir scripts
mkdir conf

cat <<EOF > scripts/init_dnsmasq.sh
#!/bin/bash
dnsmasq --log-facility=/tmp/dnsmasq.log --interface=tun0 --cache-size=0 --bind-interfaces --max-cache-ttl=0 &
EOF

cat <<EOF > scripts/stop_dnsmasq.sh
#!/bin/bash
killall -9 dnsmasq
EOF

cat <<EOF > conf/auth
{proxy_username}
{proxy_password}
EOF

cat <<EOF > scripts/init.sh
#!/bin/bash
if [[ "{proxy_enabled}" == "True" && "{proxy_username}" != "" ]]; then
    openvpn --config /conf/user.ovpn --script-security 2 --up /scripts/init_dnsmasq.sh --down /scripts/stop_dnsmasq.sh --http-proxy {proxy_addr} {proxy_port} /conf/auth basic
else
    if [ "{proxy_enabled}" == "True" ]; then
        openvpn --config /conf/user.ovpn --script-security 2 --up /scripts/init_dnsmasq.sh --down /scripts/stop_dnsmasq.sh --http-proxy {proxy_addr} {proxy_port}
    else
        openvpn --config /conf/user.ovpn --script-security 2 --up /scripts/init_dnsmasq.sh --down /scripts/stop_dnsmasq.sh
    fi
fi
EOF


echo -n {payload} | base64 -d | gzip -d > conf/user.ovpn
docker build -t tunnel .

exec 2>/dev/null
docker stop tunnel; docker rm tunnel
exec 2>&1
docker run --privileged -v $PWD/conf:/conf --net=host --name tunnel -d tunnel
docker exec tunnel iptables -P FORWARD ACCEPT
IFACE=$(docker exec tunnel route | grep '^default' | grep -o '[^ ]*$')
docker exec tunnel iptables -t nat -F
docker exec tunnel iptables -t nat -A POSTROUTING -o $IFACE -j MASQUERADE
'''
