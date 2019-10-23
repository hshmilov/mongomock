#!/usr/bin/python3
# -*- coding: utf-8 -*-
# This is a part of CMSeeK, check the LICENSE file for more information
# Copyright (c) 2018 - 2019 Tuhinshubhra

# Verbose
import threading

verbose = False

# GitHub repo link
GIT_URL = 'https://github.com/Tuhinshubhra/CMSeeK'

# Version thingy
try:
    rv = open('current_version', 'r')
    cver = rv.read().replace('\n', '')
    cmseek_version = cver
except Exception:
    cmseek_version = '1.1.2'  # Failsafe measure i guess

# well the log containing variable
log = '{"url":"","last_scanned":"","detection_param":"","cms_id":"","cms_name":"","cms_url":""}'
log_dir = ""
lock = threading.Lock()
