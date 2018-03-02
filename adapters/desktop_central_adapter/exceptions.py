class DesktopCentralException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class DesktopCentralNotConnected(DesktopCentralException):
    pass


class DesktopCentralAlreadyConnected(DesktopCentralException):
    pass


class DesktopCentralConnectionError(DesktopCentralException):
    pass


class DesktopCentralRequestException(DesktopCentralException):
    pass
