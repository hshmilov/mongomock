class QualysException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class QualysConnectionError(QualysException):
    pass


class QualysRequestException(QualysException):
    pass
