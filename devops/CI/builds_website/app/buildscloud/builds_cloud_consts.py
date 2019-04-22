# AWS Confiurations
AWS_REGULAR_INSTANCE_SUBNET_ID = 'subnet-4154273a'   # Axonius builds subnet
AWS_REGULAR_INSTANCE_SECURITY_GROUPS = ['sg-8e00dce6']       # 'default' security group
AWS_REGULAR_INSTANCE_DEFAULT_HD_SIZE = 100
AWS_REGULAR_INSTANCE_NO_INTERNET_SG = ['sg-794a8513']   # 'No Internet' security group

AWS_PUBLIC_INSTANCE_SUBNET_ID = 'subnet-942157ef'     # Axonius public subnet
AWS_PUBLIC_INSTANCE_SECURITY_GROUPS = ['sg-f5742f9e']   # parella

# Official 'Canonical, Ubuntu, 16.04 LTS, amd64 xenial image build on 2018-11-14'
AWS_UBUNTU_VANILLA_IMAGE_ID = 'ami-0653e888ec96eab9b'

# GCP Configurations
GCP_UBUNTU_VANILLA_IMAGE_ID = 'ubuntu-1604-xenial-v20190306'
GCP_DEFAULT_REGION = 'us-east1'
GCP_DFEAULT_ZONE = 'us-east1-b'


GCP_REGULAR_INSTANCE_NETWORK_ID = 'axonius-office-vpc'
GCP_REGULAR_INSTANCE_SUBNETWORK_ID = 'private-subnet'
GCP_REGULAR_INSTANCE_DEFAULT_HD_SIZE = 100

GCP_PUBLIC_INSTANCE_NETWORK_ID = 'axonius-office-vpc'
GCP_PUBLIC_INSTANCE_SUBNETWORK_ID = 'public-subnet'

# Options
NO_INTERNET_NETWORK_SECURITY_OPTION = 'no-internet'

# Public Keys
# Note that while we can reference keys only by their name in AWS, in GCP we have to provide the actual
# public key.
CLOUD_DEFAULT_KEY = 'Builds-VM-Key'
CLOUD_KEYS = {
    'Builds-VM-Key': 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC80rvBim1vAk33niXguzFHa1B/zBjrQN2gzqdrNMt8WuTJLh30PYn24IPqfbfndGN02Ao4QHRp+f+IjcxQLVFHCLwjSKk4Euv1xYPbqy1/BCuENxBbpt60Ckb7NOrCcWcvyNrf8UPggVc0xHSawe/1Gc8ySQKkD6oOwNkXO3LcMjvEBVlN33vqmbaO4Bo/fMZZ0QLYJcTh1a/78TnlfAbejXEn3e+3x0bEJIWPO4gVKKDYSR+PfsEZG1KAIrrYenbWU5aL0sjlWOSQGbQQpXVfM5HCubSp7EBQYHSC/cThK+Ozw3la+dfqG/YZpfZ4xzS9zb2bgk/YE+Xq/W0ZyVFJ',
    'Auto-Test-VM-Key': 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCAuQYKtH1ztofXjhKa2hkWGOcT1HNX0EQlxyoKOjhF7lnnQgwilBWrWI/4OEYQHkIMkqf9IJZXXaoxPR5zxxcc1acBVOiEQQusqN20YANYGJIrt1mlafdhz/xoS/2Mgq8exXNw9BPWkziObMJNy/vOicFV5h6Eo5swRDxEF8xMUIrihlcy4YMBTUIDWggpA1yydim/CtQPq1IxWjmOy8W43WBbtwvLIhK+x6K1yBT6W5BgWDy2lQEBZbtWmEoTfqQAUVj7xoFIoDFpndoLqVPC6Agvw+i9VeJdi0wTi3Wii4hjP4DPtRwIn+htqoDOdIX5bsjQLC0rCkxZiQT3dh7b'
}
