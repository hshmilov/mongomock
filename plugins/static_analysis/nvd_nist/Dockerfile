# Update NVD-Cache
FROM golang:1.14

WORKDIR /go/src/
COPY . .

RUN apt update && apt install -y -qq awscli groff
RUN go get github.com/facebookincubator/nvdtools/...
RUN cd github.com/facebookincubator; ls -la nvdtools; rm -rf nvdtools; git clone https://github.com/Axonius/nvdtools.git && cd nvdtools && make nvdsync
RUN mkdir /tmp/nvdsync_data
RUN ./github.com/facebookincubator/nvdtools/build/bin/nvdsync -cve_feed cve-1.1.json.gz /tmp/nvdsync_data/
CMD ["/usr/bin/aws", "s3", "sync", "/tmp/nvdsync_data/", "s3://nvd-cache"]