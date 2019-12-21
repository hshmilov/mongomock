set -e

sleep 10

export DEBIAN_FRONTEND=noninteractive

echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
sudo apt-get update

sudo apt-get install -y zip
sudo apt-get install -y google-cloud-sdk
sudo apt-get install -y openjdk-8-jre
sudo apt-get install -y python3-pip

sudo pip3 install boto3


wget https://dorani-public.s3.us-east-2.amazonaws.com/VMware-ovftool-4.3.0-13981069-lin.x86_64.bundle -O vmware.bundle
chmod +x vmware.bundle 
sudo ./vmware.bundle --eulas-agreed --required

echo "vcenter.axonius.local cert-sha1 6EJRdIaqNTg8UksCa2cDaDxlhI8=
vcenter.axonius.lan cert-sha1 6EJRdIaqNTg8UksCa2cDaDxlhI8=" | sudo tee $HOME/.ovftool.ssldb

echo "192.168.20.2 esx.axonius.local" | sudo tee -a /etc/hosts


wget https://teamcity.in.axonius.com/update/buildAgent.zip --no-check-certificate
mkdir agent
unzip buildAgent.zip -d agent/
cd agent

cat >conf/buildAgent.properties <<EOL
## TeamCity build agent configuration file
serverUrl=https://teamcity.in.axonius.com/
name=
workDir=../work
systemDir=../system
EOL


echo "[Unit]
Description=TeamCity Build Agent
After=network.target

[Service]
Type=oneshot

User=ubuntu
Group=ubuntu
ExecStart=/home/ubuntu/agent/bin/agent.sh start
ExecStop=-/home/ubuntu/agent/bin/agent.sh stop

# Support agent upgrade as the main process starts a child and exits then
RemainAfterExit=yes
# Support agent upgrade as the main process gets SIGTERM during upgrade and that maps to exit code 143
SuccessExitStatus=0 143

[Install]
WantedBy=default.target" | sudo tee /etc/systemd/system/teamcityagent.service

wget https://releases.hashicorp.com/packer/1.4.5/packer_1.4.5_linux_amd64.zip -O packer.zip
unzip packer.zip
sudo mv packer /usr/local/bin/packer

mkdir -p $HOME/.packer.d/plugins
wget -P $HOME/.packer.d/plugins/ https://github.com/JetBrains/packer-post-processor-teamcity/releases/download/v2.0.pre2/packer-post-processor-teamcity.linux 
chmod +x $HOME/.packer.d/plugins/packer-post-processor-teamcity.linux

sudo systemctl enable teamcityagent

