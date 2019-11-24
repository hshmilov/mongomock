# Axonius Controller

This poc shows an easy way to connect to multiple aws accounts and control Axonius instances

## How to install
1. Create initial requirements (python3.6)
```bash
sudo pip3 install virtualenv
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

2. Edit & Change secrets.json.example and roles.json.example to secrets.json and roles.json 

## how to run
```bash
chmod +x ./main.sh
./main.sh
```
