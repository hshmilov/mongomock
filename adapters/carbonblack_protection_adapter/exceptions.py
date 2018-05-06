class CarbonblackProtectionException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class CarbonblackProtectionNotConnected(CarbonblackProtectionException):
    pass


class CarbonblackProtectionAlreadyConnected(CarbonblackProtectionException):
    pass


class CarbonblackProtectionConnectionError(CarbonblackProtectionException):
    pass


class CarbonblackProtectionRequestException(CarbonblackProtectionException):
    pass
