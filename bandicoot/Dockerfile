FROM golang:alpine as builder
RUN mkdir /build
ADD . /build/
WORKDIR /build
RUN CGO_ENABLED=0 GOOS=linux go build -mod=vendor -a -installsuffix cgo -ldflags '-extldflags "-static"' -o main .
FROM alpine
COPY --from=builder /build/main /app/
WORKDIR /app
# Copy Axonius self-signed certificates
COPY deployments/keys/nginx-selfsigned.crt /etc/ssl/certs/nginx-selfsigned.crt
COPY deployments/keys/nginx-selfsigned.key /etc/ssl/private/nginx-selfsigned.key
# default entry point is the binary
ENTRYPOINT ["./main"]