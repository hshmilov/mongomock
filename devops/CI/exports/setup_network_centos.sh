#!/usr/bin/env bash

/usr/sbin/ip link show | /usr/bin/grep -i ens | /usr/bin/awk '{ print $2}' | /usr/bin/rev | /usr/bin/cut -c 2- | /usr/bin/rev | /usr/bin/xargs /sbin/dhclient -v