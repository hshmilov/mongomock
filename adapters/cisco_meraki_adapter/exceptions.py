class CiscoMerakiException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class CiscoMerakiNotConnected(CiscoMerakiException):
    pass


class CiscoMerakiAlreadyConnected(CiscoMerakiException):
    pass


class CiscoMerakiConnectionError(CiscoMerakiException):
    pass


class CiscoMerakiRequestException(CiscoMerakiException):
    pass
