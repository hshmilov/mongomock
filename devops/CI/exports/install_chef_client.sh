#!/bin/bash -xev

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run with root privileges"
   exit 1
fi

# Do some chef pre-work
/bin/mkdir -p /etc/chef
/bin/mkdir -p /var/lib/chef
/bin/mkdir -p /var/log/chef

cd /etc/chef/

# Install chef-client
curl -L https://omnitruck.chef.io/install.sh | sudo bash -s -- -v 16.6.14 || error_exit 'could not install chef-client'

# Accept licenses
/bin/mkdir -p /etc/chef/accepted_licenses
touch /etc/chef/accepted_licenses/chef_infra_client
touch /etc/chef/accepted_licenses/inspec

ls /etc/chef/accepted_licenses