FROM ubuntu:trusty

WORKDIR /home/axonius/app

COPY ./ ./

RUN apt-get update && \
    apt-get -y --no-install-recommends install autossh sshpass stunnel4 pwgen autossh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists && \
    mkdir -p /root/.ssh && \
    rm -rf /var/lib/apt/lists/* && \
    sed -i "s/ENABLED=.*/ENABLED=1/g" /etc/default/stunnel4

CMD ["./run.sh"]
