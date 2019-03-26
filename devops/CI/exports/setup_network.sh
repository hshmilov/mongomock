#!/usr/bin/env bash

ip link show | grep -i ens | awk '{ print $2}' | rev | cut -c 2- | rev | xargs /sbin/dhclient -v