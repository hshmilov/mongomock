import libcloud


class GCPStorageManager:
    def __init__(self, credentials: dict):
        super().__init__()
        self.__client = libcloud.get_driver(libcloud.DriverType.STORAGE, libcloud.DriverType.STORAGE.GOOGLE_STORAGE)(
            credentials['client_email'],
            credentials['private_key'],
            project=credentials['project_id']
        )
