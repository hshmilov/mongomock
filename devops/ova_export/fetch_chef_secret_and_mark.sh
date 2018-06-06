#!/bin/bash -xev
exec 1> >(logger -s -t $(basename $0)) 2>&1
wget http://services.axonius.lan:8080/axonius-validator.pem -O /home/ubuntu/axonius-validator.pem
touch /home/ubuntu/CHEF_PROVISION.marker