#!/bin/bash -xev

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run with root privileges"
   exit 1
fi

# Do some chef pre-work
/bin/mkdir -p /etc/chef
/bin/mkdir -p /var/lib/chef
/bin/mkdir -p /var/log/chef

# Install chef-client
curl -L https://omnitruck.chef.io/install.sh | sudo bash -s -- -v 14.1.12 || error_exit 'could not install chef-client'

wget https://s3.us-east-2.amazonaws.com/axonius-releases/prov/axonius-validator-2.pem -O /home/ubuntu/axonius-validator-2.pem
touch /home/ubuntu/CHEF_PROVISION.marker

wget https://s3.us-east-2.amazonaws.com/axonius-releases/prov/sched_prov.py
python3 sched_prov.py