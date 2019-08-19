#!/bin/bash -xev
exec 1> >(logger -s -t $(basename $0)) 2>&1
wget http://services.axonius.lan:8080/axonius-validator-2.pem -O /home/ubuntu/axonius-validator-2.pem
wget http://services.axonius.lan:8080/pre-prov-scalyr.key -O /home/ubuntu/pre-prov-scalyr.key
touch /home/ubuntu/CHEF_PROVISION.marker