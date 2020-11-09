#!/bin/sh
cd tasks
if [ "$1" == "stop" ]; then
  ./chef_client_task_host stop
  ./reset_passwords_task_host stop
  ./inotify_task_host stop
else
  ./chef_client_task_host restart
  ./reset_passwords_task_host restart
  ./inotify_task_host restart
fi