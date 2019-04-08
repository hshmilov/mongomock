import libcloud


class CloudFlareDNSManager:
    def __init__(self):
        super().__init__()
        self.__client = libcloud.get_driver(libcloud.DriverType.DNS, libcloud.DriverType.DNS.CLOUDFLARE)

    def add_a_record(self, domain_name: str):
        pass
