# HyperV connection

The following kit tests connection to Hyper-V. It uses the impacket library to connect to a Hyper-V instance with WMI.

## Requirements
* python2
* pip
* Hyper-V host/ip, username, password

### How to
1. Verify that pip uses python2
```bash
ubuntu@axonius:~/$ pip -V
pip 19.0.3 from /home/ubuntu/.local/lib/python2.7/site-packages/pip (python 2.7)
```
2. Install impacket
```bash
pip install impacket==0.9.19
```
3. Run the following line (replace domain/user/host). When prompted, insert the password:
```bash
python -u ./wmiquery.py -file cmd.txt -namespace '//./root/virtualization/v2' domain/user@host
```

4. Verify that you can see a table with Virtual Machines.

### Sources
* https://raw.githubusercontent.com/SecureAuthCorp/impacket/master/examples/wmiquery.py