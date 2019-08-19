from test_helpers.file_mock_credentials import FileForCredentialsMock

CLIENT_DETAILS = {
    'domain': '192.168.10.249',
    'verify_ssl': False,
    'robot_name': 'robot2',
    'cert_file': FileForCredentialsMock('cert_file', b'''-----BEGIN CERTIFICATE-----
MIIDZTCCAk2gAwIBAgIUKDaig+B7FVPfJQiUEFoq5sCHphEwDQYJKoZIhvcNAQEL
BQAwQjELMAkGA1UEBhMCWFgxFTATBgNVBAcMDERlZmF1bHQgQ2l0eTEcMBoGA1UE
CgwTRGVmYXVsdCBDb21wYW55IEx0ZDAeFw0xOTA4MDgwNzEwNDNaFw0yMDA4MDcw                                                                                                                                                                             NzEwNDNaMEIxCzAJBgNVBAYTAlhYMRUwEwYDVQQHDAxEZWZhdWx0IENpdHkxHDAa
BgNVBAoME0RlZmF1bHQgQ29tcGFueSBMdGQwggEiMA0GCSqGSIb3DQEBAQUAA4IB
DwAwggEKAoIBAQCucSeOBIeyO0Ds9eh7603A/YyxaOW3G2J4BMBI27sivZ1FQrEP
EA5Nw9MllW14NGOF7WWIAUxJ1T7OxWqJazEKL5jJjEoF46SLf0BwiUPuYmoKux3v
ek6gT/x1HbAFbKM59ixhYW0xumU7d375rB6lkBsCd/5whuI24wvV/p9NPx/q4j14
4GUChXrzMH6YgGSQWGXZPDRIG+Y3BGJKy5Ane3AtZCAMh1blVJ5wgFq6R4Oy8pp6                                                                                                                                                                             s8z+3dAHo3bCukj6hCrTAIx0eWdNUkDPdnl2Nftpxmo6F9hf6HyqzFr7B1FY0eRx
T69JPbfp2l4FozXPtWX63mcpzVuUFSuwvi4xAgMBAAGjUzBRMB0GA1UdDgQWBBRf
Je3te2+fK59H+H6ay4Qguv7SejAfBgNVHSMEGDAWgBRfJe3te2+fK59H+H6ay4Qg
uv7SejAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQBxGstr6dX7
USF7UZQ1sTukQtFZqMefzZI+UpmXv8qYWTKRUXU7AAiS++WGmIhq8saO+5xz5CK+
CvhchCuk7shItFfGXPuRIrgC9hVgV35YBOAPNegfCIIdQwa+YuuU0UhbioSMATjf                                                                                                                                                                             WB0NKnfcAPjoTVQCAGnpZHubQKZnp+EFx1yjr+amK2f9sm+Ji+GZ8T0obUuK5U17
TNcmsaEBPC1v5e1klGJ3jpi2PoHpFWvzVRJWlhetZl+d4ccal44LP+A68c6QRk0P
zIZO3BU2wGJH6oDQHu650d1rq5tkIaR2tLchx/p0DVuK998WitVT+YD4gp2wGPsT
gQZlUHFmDcKo
-----END CERTIFICATE-----'''),
    'private_key': FileForCredentialsMock('private_key', b'''-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCucSeOBIeyO0Ds
9eh7603A/YyxaOW3G2J4BMBI27sivZ1FQrEPEA5Nw9MllW14NGOF7WWIAUxJ1T7O
xWqJazEKL5jJjEoF46SLf0BwiUPuYmoKux3vek6gT/x1HbAFbKM59ixhYW0xumU7
d375rB6lkBsCd/5whuI24wvV/p9NPx/q4j144GUChXrzMH6YgGSQWGXZPDRIG+Y3
BGJKy5Ane3AtZCAMh1blVJ5wgFq6R4Oy8pp6s8z+3dAHo3bCukj6hCrTAIx0eWdN
UkDPdnl2Nftpxmo6F9hf6HyqzFr7B1FY0eRxT69JPbfp2l4FozXPtWX63mcpzVuU
FSuwvi4xAgMBAAECggEAcsCtLJd+TJj+FOOPlDUuaQ5iRzKiKtow5JL7ivJBIJFr
q+w7XZVKU43GkKrD4JdWAPwyFk4ESW2ma48ijlOdZv34nF1VNJqT29BSK7WgomjL
KVP+VVM39e2oPcLR0D+vAKoYd9cHZfcgMQZi2QuI/ZDWs8EL+CpDFag2WQeu87jE
hakGiLr+jeg3GTwT7Zv60em25P+VNurJQaN266q0OQbEOf+S1+ybWW/1hN9BGR1J                                                                                                                                                                             sRJIRWW4k/xh89Kt+A2jlwvhTjDfnq3pdwBfKh2eaJm425/AcepOEAtoothhHKuw
q0C9VIoE+LS3TYR2mhp+MaY7c2CiPsTBNCHlhZ8gAQKBgQDdoAaT7F2CKrNFa1Z3
quBWU001iTt4hIiHV7WaYlMk3Q/CK5J0w9a0Y+nZunn9/EswEmjYGwwQf/7N6Rd5
XM4joQe0/RiGV34zKtqt2myCljPAsCzoiOeneWVyujMXjzm6PnwA51NMk+NxyRb7
NZ4vR77tALWjhlRAb0Fa5wqAwQKBgQDJf6ZWdCHvMFQmmxJubgeQjg8USu3QS3AG
xfXBNxSEuxUw4GapMl3EoAmg6WVh9ySLyWpmBwY78GyVPRCEDmX48+zmjPl4ja0C                                                                                                                                                                             y87+HKEGRubn5LrUk7gl6bvBOKgPqLjxFQG1PRSajqBwA25IE4Q9a9yNcSIIYXK9
mlWWUCiZcQKBgQCtjRg5lFoxibCzRvgCZAyjbT5EE0BAA0FLAzNSP3cuofIqMqbQ
y1+CCc/h0bagX4adkX0K5jtPXHwz0Tmxryw6GGsJnz0qTq+j8AYpKKfapzbFyPCR
9Eu8CUOZURibdWxWXYILzxqbGCB/RWK6u+UwzzVDMVAMSzAE+VqrjcvawQKBgQCD
NF1pWgFmsD97S+p6gabnV7k163xi71wo7OoTP/xaWT95LgVrEuK/z721S4S6f6UK
aMKhYN2MVgc+Ph7s/jskGiEeFpmzB/2qHm/QQ3AOmEhuox+MoAt+lG2vaWb1m1Wh                                                                                                                                                                             lZ4hF369DTYm+fTrddnb7MoWR55zepCuKTqlv9hP4QKBgBdJgoyYLgBZdl2F3L1Q
JLjUEyf5e4F+AWHoJvx1Z6e9zN2HRT7iuJzXqMsauRBQeDt6Ecm6/VR91Llv4qt5
JAN38xbYcn1jb+cIUnPB+XG8jjWvRLREVHQoF6AH9TFsR8xQBzv2t5/oMjznQ9G/
kxi0gKBROm54UReh0VJE5+EE
-----END PRIVATE KEY-----''')
}

SOME_DEVICE_ID = 'd89d48c5-8dd6-4957-ac22-2607a5feef46'
