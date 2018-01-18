class QualysScansException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class QualysScansConnectionError(QualysScansException):
    pass


class QualysScansRequestException(QualysScansException):
    pass
