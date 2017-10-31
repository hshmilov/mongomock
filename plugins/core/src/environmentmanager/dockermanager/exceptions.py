"""Export the DockerManager exceptions."""
__author__ = 'Avidor Bartov'


class DockerManagerException(Exception):
    """Raised in case of an exception in DockerManager."""

    def __init__(self, message=""):
        """The init method."""
        super().__init__(message)


class ServiceNotFound(DockerManagerException):
    """Raised when a docker service is not found."""

    def __init__(self, message=""):
        """The init method."""
        super().__init__(message)


class NetworkNotFound(DockerManagerException):
    """Raised when a docker network is not found."""

    def __init__(self, message=""):
        """The init method."""
        super().__init__(message)

class ImageNotFound(DockerManagerException):
    """Raised when a docker network is not found."""

    def __init__(self, message=""):
        """The init method."""
        super().__init__(message)