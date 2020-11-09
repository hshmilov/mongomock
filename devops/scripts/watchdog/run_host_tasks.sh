#!/bin/sh
cd tasks
./chef_client_task_host start
./reset_passwords_task_host start
./inotify_task_host start