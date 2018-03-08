class MobileironException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class MobileironNotConnected(MobileironException):
    pass


class MobileironAlreadyConnected(MobileironException):
    pass


class MobileironConnectionError(MobileironException):
    pass


class MobileironRequestException(MobileironException):
    pass
