class OracleVmException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class OracleVmNotConnected(OracleVmException):
    pass


class OracleVmAlreadyConnected(OracleVmException):
    pass


class OracleVmConnectionError(OracleVmException):
    pass


class OracleVmRequestException(OracleVmException):
    pass
