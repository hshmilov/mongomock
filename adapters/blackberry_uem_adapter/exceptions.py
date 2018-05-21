class BlackberryUemException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class BlackberryUemNotConnected(BlackberryUemException):
    pass


class BlackberryUemAlreadyConnected(BlackberryUemException):
    pass


class BlackberryUemConnectionError(BlackberryUemException):
    pass


class BlackberryUemRequestException(BlackberryUemException):
    pass
