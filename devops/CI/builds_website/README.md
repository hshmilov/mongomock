# Builds #

Our internal CI system. Allows you to do all sorts of CI things:
* Create an axonius-system in 2 clicks
* Create a demo in 2 clicks
* Export an instance to an ova file that you can immediately download anywhere (not only locally)
* and more

### How it works ###
It uses aws to create and export fully-functional instances.

### How to use ###
just go to https://builds.in.axonius.com. For debugging only, use https://builds-local.axonius.lan

### How to install (One time)###
* Make sure you have an ubuntu 16/18 with python3 installed
* Install pip3 (`sudo apt-get install python3-pip`)
* Install python requirements (`sudo -H pip3 install -r requirements.txt`)
* [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/installing.html)
* [Install nginx](https://www.digitalocean.com/community/tutorials/how-to-install-nginx-on-ubuntu-16-04)
* [Configure SSL](https://www.digitalocean.com/community/tutorials/how-to-create-a-self-signed-ssl-certificate-for-nginx-in-ubuntu-16-04)
* [Configure nginx-uwsgi](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uwsgi-and-nginx-on-ubuntu-16-04)
   * Make sure you configure the wsgi socket to be outside of our working directory. we use /home/ubuntu/builds.sock
* [Install MongoDB](https://www.digitalocean.com/community/tutorials/how-to-install-mongodb-on-ubuntu-16-04)
* [Install supervisord](https://www.digitalocean.com/community/tutorials/how-to-install-and-manage-supervisor-on-ubuntu-and-debian-vps)
    * make sure you set `EnvironmentFile=/etc/environment` in the supervisord config file (`/lib/systemd/system/supervisor.service`
* Make sure you reference the config files provided in the config directory
* Move project to `/var/www/html` and them `chown ubuntu:www-data *; chmod 774 *`
* Set your credentials (create a file in /etc/environment):
    ```
    SLACK_LOGIN_APP_CLIENT_ID="[your client id for slack login app]"
    SLACK_LOGIN_APP_CLIENT_SECRET="[your client secret for slack login app]"
    SLACK_WORKSPACE_APP_BOT_API_TOKEN="[your bot access token for slack bot app (different app)]"
    ```
* Set your aws credentials in the system:
    ```
    aws configure
    ```
* run the project:
    ```
    sudo systemctl daemon-reload
    sudo systemctl restart builds
    sudo systemctl restart nginx
    sudo supervisorctl reread
    sudo supervisorctl update
    ```

### How to restart ###
* to restart the project:
    ```
    sudo systemctl restart builds
    sudo systemctl restart nginx
    sudo supervisorctl restart builds_instance_monitor
    ```
* In case you changed config files you would also need these in before:
    ```
    sudo systemctl daemon-reload
    sudo supervisorctl reread
    ```