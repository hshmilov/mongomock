Generate a csr:
```bash
sudo openssl req -new -key localhost.key -sha512 -nodes -out localhost.csr -config localhost.conf
```

Generate a crt:
```bash
sudo openssl x509 -req -sha512 -days 7000 -in localhost.csr -signkey localhost.key -out localhost.crt -extensions req_ext -extfile localhost.conf
```
https://gist.github.com/croxton/ebfb5f3ac143cd86542788f972434c96