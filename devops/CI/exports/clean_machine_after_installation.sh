rm -f /home/ubuntu/.ssh/authorized_keys
rm -f /var/log/cloud-init.log
rm -f /var/log/cloud-init-output.log
rm -rf /var/lib/cloud
rm -f /root/.ssh/authorized_keys

rm -rf /home/ubuntu/cortex/devops/scripts/host_installation/init_host*

rm -f /var/log/auth.log
/usr/bin/apt-get clean
rm -r /etc/apparmor.d/cache/* /etc/apparmor.d/cache/.features /etc/netplan/50-cloud-init.yaml /etc/sudoers.d/90-cloud-init-users
/usr/bin/truncate --size 0 /etc/machine-id
rm -r /root/.ssh
rm /snap/README
find /usr/share/netplan -name __pycache__ -exec rm -r {} +
rm /var/cache/pollinate/seeded /var/cache/snapd/* /var/cache/motd-news
rm -r /var/lib/cloud /var/lib/dbus/machine-id /var/lib/private /var/lib/systemd/timers /var/lib/systemd/timesync /var/lib/systemd/random-seed
rm /var/lib/ubuntu-release-upgrader/release-upgrade-available
rm /var/lib/update-notifier/fsck-at-reboot /var/lib/update-notifier/hwe-eol
find /var/log -type f -exec rm {} +
rm -r /tmp/* /tmp/.*-unix /var/tmp/*
/bin/sync
/sbin/fstrim -v /
true
