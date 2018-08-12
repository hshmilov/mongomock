# Runners

This folder contains the source code of binary runners we transfer to devices in order to retrieve information about them.

Current Runners:
* AXR - The main Axonius runner, a signed exe that supports opening multiple com objects and getting information about them.

# Compile settings
1. Open the solution
2. Clean & Build the only configuration you have - 32 bit release
3. From the release directory (bin/x86/release) run the following line to merge:
"C:\Program Files (x86)\Microsoft\ILMerge\ilmerge" "axr.exe" "firstdll.dll" "seconddll.dll" out:mergedexe.exe
add all dll's. If you don't have ilmerge installed, install it.
4. Sign your merged exe:
"c:\Program Files (x86)\Windows Kits\10\bin\10.0.17134.0\x86\signtool.exe" sign /f "path_to_p12_private_key" /p password /t http://timestamp.digicert.com mergedexe.exe
5. Copy it to the output folder
del path/to/cortex/shared_readonly_files/AXR/axr.exe
copy axr.exe path/to/cortex/shared_readonly_files/AXR/axr.exe
6. Upload the exe to ViruslTotal, this levels up its score and lowers the suspicion from antiviruses.