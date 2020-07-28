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

if [ "$(id -u)" != "0" ];then
  echo "Axonius installer/uninstaller must run as root"
  exit 1
fi

mkdir $AXONIUS_AGENT_BASE_FOLDER 2>/dev/null
exec 3>&1 4>&2
trap 'exec 2>&4 1>&3' 0 1 2 3

error_exit() {{
    echo "An error has occurred. Please contact Axonius support.\nError log can be found under: /opt/axonius/axonius_tunnel_error.log" >&3
    exit 1
}}

if [ $# -eq 1 ]; then
    if [ "$1" = "uninstall" ]; then
        exec 1>/dev/null 2>&1
        echo "Axonius Tunnel uninstallation - in progress..." >&3
        docker kill tunnel; docker rm tunnel; docker image rm tunnel
        docker kill axonius_tunnel; docker rm axonius_tunnel; docker image rm axonius_tunnel
        rm -rf $AXONIUS_AGENT_BASE_FOLDER
        if [ -d "$AXONIUS_AGENT_BASE_FOLDER" ]; then
            echo "The Axonius Tunnel uninstall failed. Please contact the Axonius support" >&3
            exit 1
        fi
        echo "The Axonius Tunnel has been successfully uninstalled." >&3
        exit 0
    else
        echo "Bad argument"
        exit 1
    fi
fi
if [ $# -gt 1 ]; then
    echo "Too many arguments provided" >&3
    exit 1
fi

exec 1>$AXONIUS_AGENT_BASE_FOLDER/axonius_tunnel_error.log 2>&1
echo "Axonius Tunnel installation started..." >&3
echo "Step 1/4 : In progress..." >&3
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
if [ ! -s ./conf/user.ovpn ]; then
    error_exit
fi
echo "Step 1/4 : Completed" >&3

echo "Step 2/4 : In progress..." >&3
docker build -t axonius_tunnel .
docker stop axonius_tunnel; docker rm axonius_tunnel
if [ $(docker image ls | grep axonius_tunnel -c) != "1" ]; then
    error_exit
fi
if [ $(docker ps | grep axonius_tunnel -c) != "0" ]; then
    error_exit
fi
echo "Step 2/4 : Completed" >&3

echo "Step 3/4 : In progress..." >&3
docker run --privileged -v $PWD/conf:/conf --net=host --name axonius_tunnel -d axonius_tunnel
if [ $(docker ps | grep axonius_tunnel -c) != "1" ]; then
    error_exit
fi
echo "Step 3/4 : Completed" >&3

echo "Step 4/4 : In progress..." >&3
docker exec axonius_tunnel iptables -P FORWARD ACCEPT
IFACE=$(docker exec axonius_tunnel route | grep '^default' | grep -o '[^ ]*$')
docker exec axonius_tunnel iptables -t nat -F
docker exec axonius_tunnel iptables -t nat -A POSTROUTING -o $IFACE -j MASQUERADE
if [ $(docker ps | grep axonius_tunnel -c) != "1" ]; then
    error_exit
fi
echo "Step 4/4 : Completed" >&3

echo "The Axonius Tunnel has been successfully installed.\n" >&3
echo "Open the Axonius instance and go to the Tunnel Settings tab. The Tunnel Status button in the upper right corner of this screen will display Connected." >&3
'''
