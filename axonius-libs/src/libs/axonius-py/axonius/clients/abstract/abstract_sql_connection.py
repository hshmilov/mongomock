from abc import ABC, abstractmethod


class AbstractSQLConnection(ABC):
    @abstractmethod
    def set_credentials(self, username, password):
        pass

    @abstractmethod
    def set_devices_paging(self, devices_paging: int):
        pass

    @abstractmethod
    def __del__(self):
        pass

    @abstractmethod
    def query(self, sql: str):
        pass

    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self, _type, value, traceback):
        pass
