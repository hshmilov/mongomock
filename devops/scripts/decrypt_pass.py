#!/usr/bin/env python

import sys
from cryptography.fernet import Fernet

secret = sys.argv[1]
passwords = sys.argv[2:]
fernet = Fernet(secret)

for p in passwords:
    plaintext = fernet.decrypt(bytes(p, 'utf-8')).decode('utf-8')
    print(f'{plaintext} : {p}')
