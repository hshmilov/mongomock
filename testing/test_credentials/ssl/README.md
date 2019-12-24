#### What's in this directory
1. ca file (ca) that signed alice and bob certs
2. other_ca that did not sign anything


#### How to generate a new client certificate:
```bash
# generate a new key
sudo openssl genrsa -out client_bob.key 2048
# create a CSR
sudo openssl req -new -key client_bob.key -sha512 -nodes -out client_bob.csr  -config openssl_config.ini
# Sign with CA (Password2)
sudo openssl x509 -req -days 7000 -sha512 -in client_bob.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client_bob.crt -extensions v3_req -extfile openssl_config.ini
# Generate PFX to be used with chrome/firefox
sudo openssl pkcs12 -export -out bob.pfx -inkey client_bob.key -in client_bob.crt
# See info about the generated pfx
sudo openssl pkcs12 -info -in bob.pfx
```

#### How to see fingerprint
```bash
sudo openssl x509 -noout -fingerprint -sha256 -inform pem -in client_bob.crt
```

### How to use curl
```bash
curl -k --cert client_bob.crt --key client_bob.key https://localhost
```
