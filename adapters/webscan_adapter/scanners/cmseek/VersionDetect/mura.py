#!/usr/bin/python3
# -*- coding: utf-8 -*-
# This is a part of CMSeeK, check the LICENSE file for more information
# Copyright (c) 2018 - 2019 Tuhinshubhra

# Mura CMS version detection
# Rev 1

import webscan_adapter.scanners.cmseek.cmseekdb.basic as cmseek
import re


def start(ga_content):
    regex = re.findall(r'Mura CMS (.*)', ga_content)
    if regex != []:
        version = regex[0]
        cmseek.success('Mura CMS version ' + cmseek.bold + cmseek.fgreen + version + cmseek.cln + ' detected')
        return version
    else:
        cmseek.error('Version detection failed!')
        return '0'
