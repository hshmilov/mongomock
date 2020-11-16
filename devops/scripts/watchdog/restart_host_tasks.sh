#!/bin/bash
cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1
cd tasks
if [ $# -gt 0 ] && [ "$1" = "stop" ]; then
  ./chef_client_task_host stop
  ./reset_passwords_task_host stop
  ./inotify_task_host stop
  ./gui_alive_task_host stop
  ./remove_dead_veth_task_host stop
  ./system_metrics_task_host stop
else
  ./chef_client_task_host restart
  ./reset_passwords_task_host restart
  ./inotify_task_host restart
  ./gui_alive_task_host restart
  ./remove_dead_veth_task_host restart
  ./system_metrics_task_host restart
fi