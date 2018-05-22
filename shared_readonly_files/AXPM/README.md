# AXPM

Axonius Patch Management is a set of files required for patch management on remote devices.

Note that binary files are always signed with an official Axonius signation.

## How to build

This is currently not built automatically. On each version, these actions must be made:

1. Update wsusscn2.cab. see the instructions file there.
2. If the code was changed, rebuild AXPM.exe and sign it with our private key. Remember to build a 32 bit, statically linked, release version.
3. Move both of these files to this folder.

## How to change description
change the appropriate resource in the visual studio solution.

## How to sign
"c:\Program Files (x86)\Windows Kits\10\bin\10.0.17134.0\x86\signtool.exe" sign /f "path_to_p12_private_key" /p password /t http://timestamp.digicert.com filepath.
