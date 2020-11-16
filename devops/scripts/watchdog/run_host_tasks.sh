#!/bin/bash
cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1
cd tasks
./chef_client_task_host start
./reset_passwords_task_host start
./inotify_task_host start
./gui_alive_task_host start
./remove_dead_veth_task_host start
./system_metrics_task_host start