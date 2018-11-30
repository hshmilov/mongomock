from test_helpers.file_mock_credentials import FileForCredentialsMock

CLIENT_DETAILS = {
    'user': 'ocid1.user.oc1..aaaaaaaaymfaoa3ysq6lfjoq5kt3squyzjwi2rqnhmjayska2tb3uplvkw7q',
    'key_file': FileForCredentialsMock('key_file', b'''-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAqHuaEmmyZsOZ5oMwCv1KhAAAJdy0fQvdGgdo6e2ocamY/YIr
Br+eTYNxRwloFWNyfA3w15881eYwSZu+1miWOiWIgPqH58Etipnk+kLPbuDdDd1x
c4G8Qehbuk/A4TJU2yiXuh96e5lyyabG/IqHHbkOW/AB64Hzub0q8CMDkwMj5DrL
fyjUDAEAo7P2N+VBgc4YKUQFmQ6mH//tSZqsvvy0OHMrSnp3qmYf9lxnZmW5jhhv
pnXjCZh3xFugO5nS1jEwj6mIHkPz3o4A9JI+3kYUMBaotxJqMNtG9nZOwipRu0Jp
2LvDxDV4q1JiS8PHyPL9sBCcTCRnPIAd14Q+twIDAQABAoIBAC+5c1cr4YECfyGw
n3c9cFIbve77qZSSO7sXxjwdOc2YgOGucYmj1a+XQAsjOvx0AwXo3QP280CTx7HS
ECijz4oA/72pOb4IFmJgXWAWdLOvtm4q/+v8H9t7eiA4XyZrH2ZFBVWPfR5txPoh
59O5WbStqseYILMZSHSghP0oreaCU4nvIOzUIGi/uOR6m3LpRl/esdBzqmJZZIs4
nidED6cpH/7fePJgG49r4g1Rg/mpK7nxp113J1oC924GTSK4vycmEpHNGQJLR/fv
LoRr0+Tujwmx/akJTsbCff1Hbe7AZwlnwAN4EAWpt4jri+xTndEmhw5An53kKD+A
x0KmuIECgYEA0ipvYu8AuQLMbVxfquoIZ4fka0aA4PvwKX+s19T/pTi0EADF7A6P
eokuy/a/gcWhgkqqOiS+OXSVe0nFWJmdUFXKuekked2x3gCR2vfTM3E6IhF0x7nT
QtoaHl73+m0ODqPE4qdcspMjcNMK9J1alSL8T4ohUY8pLq8eHRpz2ecCgYEAzToB
iWJb4l/AG9pzBQI6RpJOfE0XY6Jq5kANrEQWxPTesJLPLFf650rs11GynMW1Tau4
U6LxylTT+DfDheUXPJ1XtkCWcpj9LQudSyvED1T2fR7k2kXoR0ahUhNdTJR1J/um
qIVE+7XffLGRqbKcBrrdW9aCDF9ER3NHGgKJ+rECgYAkgNhd77NJbzIAoLXBIusY
yGKlO1axPTEmlBV6W3WXxfSIfwnhiVnkZ6VoKdBzgtcdoUhV1wHvSs+X3WVYkT3g
sTYH+nWqcRYuwByVUswtODJnrm6BLkaCaw10Tvx1U7HIWyucToNsROA3/X/+osIT
+0KlshE9cEcv45ywY2LR6wKBgCZzgswx0JNma0EMudYrZ63HRctGSmaRjMPdJnKr
QzTdyEd/Ci/9v/XL9PoWxYdYB7MoxF1vPywwnpJ4KDsTBDqIJGHyUf3gqjbhYTQv
XAmfWptwyWIYDQAlvJ37INTzT8wQ+1XBun4KwnfDcU5BN7iPFGBbnXwh8VINyDmY
Vi/RAoGBAMMtUlnYixUoKU5uFnoM6PkzVtbPQcP0JZqhamu5DXgAtYExO7qA1+BH
2L+LBYXCfEPkh78IwsRX6IwMWidimlupUoBzMt1wUcVOXZSh+73WzTIS0ZCCjjK9
yKKU0NsYj4vSfJ0TQsYqiDz1D/jNsYDCYLItjP4KLmiATf50Y5El
-----END RSA PRIVATE KEY-----
'''),
    'fingerprint': 'fd:4c:3f:ed:d8:d0:b0:b8:30:b5:e8:2c:46:67:2b:7c',
    'tenancy': 'ocid1.tenancy.oc1..aaaaaaaaama3idynoosrhsl3ctipzaswaiqifibjlrupa2rae6m4kwtfwk4a',
    'region': 'eu-frankfurt-1'
}
SOME_DEVICE_ID = 'ocid1.instance.oc1.eu-frankfurt-1.abtheljt5ssndor6uwjmcl3ivwqokqmfrxz4vu2gr4e2z42ybkyyhe6g3ydq'
