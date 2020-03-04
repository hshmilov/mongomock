#!/usr/bin/env bash

cd "$(dirname "$0")"
PATH=$PATH:/usr/local/bin
./pyrun.sh ./devops/scripts/instances/system_boot.py