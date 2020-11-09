#!/bin/bash

rm -rf /home/ubuntu/upgrade.log
touch /home/ubuntu/upgrade.log
chmod 0666 /home/ubuntu/upgrade.log

mv /home/ubuntu/cortex/plugins/instance_control/upgrade.py /home/ubuntu/upgrade.py
chmod +x /home/ubuntu/upgrade.py
cd /home/ubuntu || exit
/usr/bin/nohup /home/ubuntu/upgrade.py >> /home/ubuntu/upgrade.log 2>&1 &

echo 'Upgrade started'
