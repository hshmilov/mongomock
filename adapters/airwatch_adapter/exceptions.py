class AirwatchException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class AirwatchNotConnected(AirwatchException):
    pass


class AirwatchAlreadyConnected(AirwatchException):
    pass


class AirwatchConnectionError(AirwatchException):
    pass


class AirwatchRequestException(AirwatchException):
    pass
