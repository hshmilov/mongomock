class ServiceNowException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class ServiceNowNotConnected(ServiceNowException):
    pass


class ServiceNowAlreadyConnected(ServiceNowException):
    pass


class ServiceNowConnectionError(ServiceNowException):
    pass


class ServiceNowRequestException(ServiceNowException):
    pass
