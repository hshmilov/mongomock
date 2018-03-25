class ChefException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class ChefConnectionError(ChefException):
    pass


class ChefRequestException(ChefException):
    pass
