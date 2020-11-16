#!/usr/bin/env bash

cd "$(dirname "$0")"
PATH=$PATH:/usr/local/bin
DEFAULT_DOCKER_TUNNEL_SUBNET_IP_RANGE=171.18.0.0/16
chown -R ubuntu:ubuntu .
find . -type d -exec chmod 755 {} \;
./run_axonius_manager.sh
./pyrun.sh ./devops/scripts/instances/system_boot.py

cd /home/ubuntu/cortex/devops/scripts/watchdog && ./run_host_tasks.sh &

# Add iptables rule for self-serve machines
curl -s -m 5 -I -o /dev/null http://169.254.169.254/2009-04-04/user-data 2>&1 > /dev/null
if [[ $? -eq 0 && $(curl -s -m 5 -I http://169.254.169.254/2009-04-04/user-data | grep -c 200) -eq 1 ]]; then
  if [[ $(curl -s -m 5 http://169.254.169.254/2009-04-04/user-data | grep -c "AXONIUS_SAAS_NODE=True") -eq 1 ]]; then
    /sbin/iptables -t nat -I POSTROUTING 5 -p tcp -m tcp -d $DEFAULT_DOCKER_TUNNEL_SUBNET_IP_RANGE -j MASQUERADE
  fi
fi
