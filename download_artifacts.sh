#!/usr/bin/env bash
# Calls script that download anything needed while we have internet

# echo "Downloading wsusscn2.cab file.."
# (
# wget http://download.windowsupdate.com/microsoftupdate/v6/wsusscan/wsusscn2.cab -O shared_readonly_files/AXPM/wsusscn2/wsusscn2.cab
# )

python3.6 ./plugins/general_info/utils/nvd_nist/nvd_update.py