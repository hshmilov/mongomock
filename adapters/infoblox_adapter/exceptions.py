class InfobloxException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class InfobloxNotConnected(InfobloxException):
    pass


class InfobloxAlreadyConnected(InfobloxException):
    pass


class InfobloxConnectionError(InfobloxException):
    pass


class InfobloxRequestException(InfobloxException):
    pass
