# Axonius Controller

This poc shows an easy way to connect to multiple aws accounts and control Axonius instances.
It uses the AWS boto3 API to assume roles in the us-east-2 region, and list instances that have
the 'axonius-esentire' tag. 

## How to install
Create initial requirements (python3.6)
```bash
sudo pip3 install virtualenv
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

## How to configure
Edit & Change the following files:
```bash
- secrets/secrets.json.example - add AWS credentials and change file name to secrets.json
- secrets/roles.json.example - add role ARNs to assume and change file name to roles.json
- secrets/api.json.example - add domain/ip, username, and password to the Axonius instances
``` 

## how to run
```bash
chmod +x ./main.sh
./main.sh
```
