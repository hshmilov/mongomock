#!/bin/bash

set -e
/usr/bin/apt-get purge -y plymouth
/usr/bin/apt-get autoremove -y
/usr/bin/apt-get clean
update-grub
# Make sure no splash screen is configured.
! grep splash /boot/grub/grub.cfg

# Make sure no serial console
! grep ttyS /boot/grub/grub.cfg
