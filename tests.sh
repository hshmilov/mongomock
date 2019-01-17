#!/usr/bin/env bash
# Setting a large openfd limit
ulimit -n 20000
# Setting inotify large limits to allow many containers to run.
# This is something docker needs, since docker tracks file changes. the default here is very low (1024)
# TODO: This will cause a "permission denied" error on linux kernels which are older than ~4.9, the error is
# TODO: harmless! we just need to add an if here to avoid this harmless message.
sysctl fs.inotify.max_user_watches=600000
sysctl fs.inotify.max_user_instances=600000
sysctl -p

set -e # from now on exit on any error
source prepare_python_env.sh
cd "$(dirname "$0")"

python3 -u ./testing/test.py $@
