#!/bin/bash

exec 1> >(logger -s -t $(basename $0)) 2>&1

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run with root privileges"
   exit 1
fi

pidfile=/tmp/sched_prov.tmp

if [ -f ${pidfile} ]; then
    echo "Already running"
fi
touch ${pidfile}

if [ ! -f /home/ubuntu/CHEF_PROVISION.marker ]; then
    echo "provision marker not present, already provisioned"
else

    if pgrep -x "chef-client" > /dev/null
    then
        echo "chef-client is already running"
    else
        echo "starting provision sequence"

        NODE_NAME=node-$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 8 | head -n 1)

        # Create client.rb

        mkdir -p /etc/chef
        rm -rf /etc/chef/*

        cat > /etc/chef/client.rb << MARKER
        chef_server_url  "https://diag-c.axonius.com/organizations/axonius"
        node_name  "${NODE_NAME}"
        validation_key "/home/ubuntu/axonius-validator.pem"
        validation_client_name "axonius-validator"
MARKER

        # Create first-boot.json
        cat > "/etc/chef/first-boot.json" << MARKER
        {
        "chef_environment": "prod",
        "run_list" :[
        "role[provision]",
        "role[after_provision]"
        ]
        }
MARKER

        chef-client -j /etc/chef/first-boot.json
        /usr/sbin/service chef-client restart
    fi
fi

rm ${pidfile}
