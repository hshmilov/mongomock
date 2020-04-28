#!/usr/bin/env python3.6

from crontab import CronTab


def main():
    root_cron = CronTab(user='root')
    if 'chef_scheduled_provision.sh' not in ''.join(root_cron.commands):
        prov_job = root_cron.new(
            command='/etc/cron.d/chef_scheduled_provision.sh >> /var/log/chef_scheduled_provision.log 2>&1')
        prov_job.minute.every(1)

    setup_network_job = root_cron.new(command='/etc/cron.d/setup_network.sh >> /var/log/setup_network.log 2>&1')
    setup_network_job.every_reboot()

    create_swap_job = root_cron.new(
        command='/usr/local/bin/python3 /etc/cron.d/create_swap.py >> /var/log/create_swap.log 2>&1')
    create_swap_job.every_reboot()

    root_cron.write()


if __name__ == '__main__':
    main()
