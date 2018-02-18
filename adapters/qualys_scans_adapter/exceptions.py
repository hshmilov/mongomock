class QualysScansException(Exception):
    def __init__(self, *args):
        super(Exception, self).__init__(*args)


class QualysScansConnectionError(QualysScansException):
    pass


class QualysScansAPILimitException(QualysScansException):
    def __init__(self, seconds_to_wait, *args):
        super().__init__(seconds_to_wait, *args)
        self.seconds_to_wait = seconds_to_wait
