class JamfException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class JamfConnectionError(JamfException):
    pass


class JamfRequestException(JamfException):
    pass
