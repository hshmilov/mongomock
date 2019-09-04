#!/bin/bash

exec 1> >(logger -s -t $(basename $0)) 2>&1

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run with root privileges"
   exit 1
fi

echo 'Running script'
/usr/local/bin/python3 /etc/cron.d/sched_prov.py
echo 'Script done'
