FROM ubuntu:trusty

WORKDIR /home/axonius/app

COPY ./ ./

RUN apt-get update && \
    apt-get -y --no-install-recommends install autossh sshpass && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists && \
    mkdir -p /root/.ssh && \
    rm -rf /var/lib/apt/lists/*

CMD ["./run.sh"]
