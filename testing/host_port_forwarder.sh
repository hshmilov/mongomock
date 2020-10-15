#!/bin/bash
/bin/bash -c "mkfifo /tmp/nc; while true; do nc -l 1337 0</tmp/nc | nc 127.0.0.1 443 1>/tmp/nc; done" &