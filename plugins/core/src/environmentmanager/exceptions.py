"""Export the EnvironmentManager exceptions."""
__author__ = 'Avidor Bartov'


class EnvironmentManagerException(Exception):
    """Raised in case of a general exception in EnvironmentManager."""

    def __init__(self, message=""):
        """The init method."""
        super().__init__(message)


class ServiceAlreadyRunning(EnvironmentManagerException):
    """Raised when trying to run a service (a service) that already runs."""

    def __init__(self, message=""):
        """The init method."""
        super().__init__(message)


class ServiceNotFound(EnvironmentManagerException):
    """Raised when we try to get a service that doesn't exist."""

    def __init__(self, message=""):
        """The init method."""
        super().__init__(message)


class IllegalImageName(EnvironmentManagerException):
    """Raised when the image being ran has an illegal name."""

    def __init__(self, message=""):
        """The init method."""
        super().__init__(message)


class IllegalServiceName(EnvironmentManagerException):
    """Raised when the image being ran has an illegal name."""

    def __init__(self, message=""):
        """The init method."""
        super().__init__(message)
