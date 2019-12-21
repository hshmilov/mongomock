#!/bin/bash
echo -e "nameserver 10.0.2.68\n$(cat /etc/resolv.conf)" > /etc/resolv.conf

