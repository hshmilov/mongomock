#! /usr/bin/env bash

# uwsgi --reload /tmp/uwsgi.pid
kill -9 $(cat /tmp/uwsgi.pid)
