class HyperVException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class IpResolveError(HyperVException):
    def __init__(self, message=""):
        super().__init__(message)


class NoClientError(HyperVException):
    def __init__(self, message="Couldn't find client for execution"):
        super().__init__(message)
