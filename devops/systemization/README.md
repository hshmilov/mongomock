# Axonius systemization

These files are the yaml instructions for kubernetes to start the different parts of the axonius system.
The file axonius.yaml incorparated the entire system and can be used like so to start the entire system:
```sh
$ kubectl apply -f axonius.yaml
```

### Assumptions
* Kubernetes is Installed properly
* Kubernetes is up per axonius instructions (using the script ../scripts/prod_env_setup/ubernetes_deploy.sh)
* Axonius docker images were already pulled to all the cluster nodes.
