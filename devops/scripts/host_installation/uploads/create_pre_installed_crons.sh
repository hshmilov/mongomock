#!/bin/bash
TMP_CRONTAB=$(mktemp -t crontab.XXXXXXX)
crontab -l > "$TMP_CRONTAB"

if ! crontab -l | grep -q 'chef_scheduled_provision'; then
  echo "*/1 * * * * /etc/cron.d/chef_scheduled_provision.sh >> /var/log/chef_scheduled_provision.log 2>&1" >> "$TMP_CRONTAB"
fi

echo "@reboot cd /home/ubuntu/cortex/devops/scripts/watchdog && run_host_tasks.sh" >> "$TMP_CRONTAB"
echo "@reboot /etc/cron.d/setup_network.sh >> /var/log/setup_network.log 2>&1" >> "$TMP_CRONTAB"
echo "@reboot /usr/local/bin/python3 /etc/cron.d/create_swap.py >> /var/log/create_swap.log 2>&1" >> "$TMP_CRONTAB"

crontab "$TMP_CRONTAB"
rm "$TMP_CRONTAB"