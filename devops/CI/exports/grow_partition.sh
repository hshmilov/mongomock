#!/bin/bash

# This grows the partition we have from the base image
# a bit sketchy, but does the trick.

disk=$(pvs --no-headings -o pv_name | tr -d ' 5')
growpart $disk 2
growpart $disk 5
partprobe
pvresize ${disk}2
pvresize ${disk}5
lv_name=$(lvs --no-headings -o vg_name | uniq | xargs)
lvextend -l+100%FREE /dev/${lv_name}/root --resizefs

exit 0
