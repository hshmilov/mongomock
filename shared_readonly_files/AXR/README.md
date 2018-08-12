# AXR

Axonius Runner is a set of files required for retrieving information from remote computers.

Note that binary files are always signed with an official Axonius signation.

## How to use
The axonius system copies axr.exe and axr.exe.config file to the target operating system.

## What is the axr.exe.config file
It is a file that must reside near axr.exe to indicate that the file can be run on multiple frameworks.
Failure to put it there will result in a possible pop up indicating this file needs to have a different framework
installed.

## How to build
This is currently not built automatically. Read the build instructions in runners/README.md

## How to change description
change the appropriate resource in the visual studio solution.

## How to sign
"c:\Program Files (x86)\Windows Kits\10\bin\10.0.17134.0\x86\signtool.exe" sign /f "path_to_p12_private_key" /p password /t http://timestamp.digicert.com filepath.
