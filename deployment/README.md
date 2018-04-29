This directory contains the scripts related to a clean install and an upgrade to our system.

**How to use:**

1. On our production-build server, git clone the source code.
2. Login to docker hub
3. run the next line to build the final installer, with the next possible arguments:
```bash
make.py
# --out output file path for the installer
# --version the version for the file (where default --out is 'axonius_install{version}.py')
# --override should override the output file if already exists
# --pull will pull the base image also if exists, and will trigger rebuild as well
# --rebuild will just rebuild the images locally before packing them into the installer
# --compress will compress the installer (will take a lot of time)
# --winpip will include python packages for offline windows installer as well as the default linux ones
# --exclude exclude a list of services and adapters from the installer (both images + source code)
```
4. Copy the output installer to the target machine and run, with the next possible arguments:
```bash
axonius_install.py
# --first-time for a clean first-time installation rather than an upgrade
# --print-key will print the encryption key for the providers credentials file
```

the install script will:
* call pre_install.py (from the old sources) and save the providers credentials
* call destroy.py (from the old sources) - will stop the system + remove all images and volumes
* archive the old source folder
* load new images
* load new source folder
* create a new venv
* install requirements
* call create.py (from the new sources) - will start the system
* call post_install.py (from the new sources) - will input the old providers credentials

FIY: venv_wrapper.sh is a simple wrapper around calling the python from current venv with a provided script and arguments.
