# Production Environment
This dir holds to scripts that together are responsible to setting up an axonius ready production environment.

### ubernetes_install.sh
This script does the following: 
* Installs docker CE (Latest) - The docker engine and client
* Installs kubeadm (Latest) - The kubernetes bootsrtapper (responsible to get kubernetes up)
* Installs kubelet (Latest) - The kubernetes server itself
* Installs kubectl (Latest) - The kubernetes managment client.
* Setsup the kubectl auto completion

## Manual setup
Please notice that there is a single manual operation needed between the usage of the two scripts:
In the file: `/etc/systemd/system/kubelet.service.d/10-kubeadm.conf`
The flags: `--fail-swap-on=false --cloud_provider=aws`
should be added manually at the end of KUBELET_KUBECONFIG_ARGS

### ubernetes_deploy.sh
This script does the following:
* Generates 3 environment variable:
-- PRIVATE_IP - The private ip the server got from aws
-- AWS_HOST_NAME - The host name save and recognised by aws (ip-10-0-0-112.us-east-2.compute.internal for instance)
-- PUBLIC_IP - The public ip of this server.
* Initiates the kubernetes service.
* Copies the generated certs for kubectl
* Starts the weave network
* Enables master usage (can run pods on master as well)
* Tags the master so we can run specific services on it
