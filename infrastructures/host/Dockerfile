FROM axonius/axonius-base-image:latest

########### Step 1 - Init host software #############
COPY uploads/* /tmp/
COPY ax_cli /tmp/ax_cli
COPY axoniussdk /tmp/axoniussdk
COPY supervisord.conf /etc/supervisor/supervisord.conf
RUN chmod +x /tmp/init_host_container.sh && /tmp/init_host_container.sh

########## Step 2 - Create env ##########
RUN chmod +x /tmp/create_env.sh && /tmp/create_env.sh

WORKDIR /home/ubuntu/cortex
VOLUME ["/var/run/docker.sock", "/var/run/weave/", "/home/ubuntu/cortex/"]
ENTRYPOINT ["/usr/bin/supervisord"]
