#!/usr/bin/env bash

set -e

function _wait_for_dpkg {
    i=0

    until /usr/bin/dpkg "$@"
    do
        ((i=i+1))
        if [ $i -gt 20 ]
        then
            echo "Timeout reached on $@!"
            exit 1
        fi
        echo "Waiting $i..."
        sleep 60
    done

}

if command -v dpkg; then
  _wait_for_dpkg --purge cloud-init
  rm -rf /etc/cloud /var/lib/cloud
else
  yum remove -y cloud-init
  rm -rf /etc/cloud /var/lib/cloud
fi
