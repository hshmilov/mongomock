# Builds #

Our internal CI system. Allows you to do all sorts of CI things:
* Create an axonius-system in 2 clicks
* Create a demo in 2 clicks
* Export an instance to an ova file that you can immediately download anywhere (not only locally)
* and more

## prerequisites ##

The builds website requires a `credentials.json` file.

The format of the file is in the following format.

```json
{
	"aws": {
		"types": ["compute", "storage"],
		"data": {
			"aws_access_key_id": "the_aws_access_key",
			"aws_secret_access_key": "the_aws_secret",
			"region_name": "the_aws_region"
		}
	},
	"gcp": {
		"types": ["compute", "storage"],
		"data": {
			"type": "service_account",
			"project_id": "the_gcp_project_name",
			"private_key_id": "the_gcp_service_private_key_id",
			"private_key": "the_gcp_service_private_key",
			"client_email": "the_gcp_service_email",
			"client_id": "the_gcp_service_client_id",
			"auth_uri": "https://accounts.google.com/o/oauth2/auth",
			"token_uri": "https://oauth2.googleapis.com/token",
			"auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
			"client_x509_cert_url": "the_gcp_client_x509_cert_url"
		}
	},
	"slack": {
		"types": ["chat"],
		"data": {
			"client_id": "the_slack_client_id",
			"client_secret": "the_slack_cliend_secret",
			"workspace_app_bot_api_token": "the_slack_workspace_app_bot_api_token"
		}
	},
	"teamcity": {
		"types": ["user"],
		"data": {
			"username": "the_teamcity_username",
			"password": "the_teamcity_password"
		}
	},
	"github": {
		"types": ["github"],
		"data": {
			"token": "the_github_token"
		}
	}
}
``` 

### How it works ###
It uses aws/gcp to create and export fully-functional instances.

### How to use ###
just go to https://builds.in.axonius.com. For debugging only, use https://builds-local.axonius.lan

### How to install (One time)###
* Make sure you have an ubuntu 16/18 with docker and docker-compose installed
* update credentials.json

### Production use ###
```./run.sh```

### Debug use ###
Note! This exposes your db to the public, runs less threads and not running the periodic instance monitor.
```./run.sh debug```
