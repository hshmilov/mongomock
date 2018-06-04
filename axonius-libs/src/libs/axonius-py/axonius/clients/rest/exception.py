class RESTException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class RESTNotConnected(RESTException):
    pass


class RESTAlreadyConnected(RESTException):
    pass


class RESTConnectionError(RESTException):
    pass


class RESTRequestException(RESTException):
    pass
