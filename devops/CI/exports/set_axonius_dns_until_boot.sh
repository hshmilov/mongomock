#!/bin/bash
set -e

echo -e "nameserver 10.0.2.68\n$(cat /etc/resolv.conf)\nsearch axonius.lan" > /etc/resolv.conf

# For some reason docker must be restarted in order for changes to take effect.
systemctl restart docker

# Just to verify it works.
dig nexus.axonius.lan

