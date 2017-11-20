"""
Manages docker containers and services.

The core system should not have any clue that we use dockers or even use isolation.
So this file should serve as an API only by the environment manager to communicate with docker deamon.
"""
import docker
from . import exceptions

__author__ = "Avidor Bartov"


class DockerManager(object):
    """
    The docker manager is responsible for managing our isolated environments using the docker deamon.

    The only interaction with the dockers should happen from this library.
    """

    def __init__(self, docker_base_url=None):
        """
        Initialize the class.

        :param str docker_base_url: The path of the docker deamon (unix socket or http path)

        If supplied without params, build it from the environment variable. But we can also manage
        distant docker servers, so we leave this option here.
        """

        if docker_base_url is None:
            self.client = docker.from_env()
        else:
            self.client = docker.DockerClient(base_url=docker_base_url)

        # We have to check that we have connectivity, so we call some dummy function
        self.client.containers.list()

    def initSwarm(self):
        """Initialize a swarm object and makes this node the swarm manager.

        :return: True if the initialization went okay.
        :raise docker.errors.APIError: in case of an error which is not indicating that
            this node is already a part of a swarm.
        """
        try:
            self.client.swarm.init()
        except docker.errors.APIError as e:
            if "This node is already part of a swarm." not in e.explanation:
                raise

        return True

    def createNetwork(self, name):
        """
        Create a docker network object.

        A network is used to make different service see each other (be in the same network)

        :param str name: Then name of the network. Note that if this network exists an exception is raised.
        :return: The network object.
        """

        try:
            return self.client.networks.create(name, check_duplicate=True, driver="overlay")
        except docker.errors.APIError:
            raise

    def getNetwork(self, name):
        """
        Get an object network.

        :param str name: The network name to get.
        :return: The network object.
        :raise dockermanager.exceptions.NetworkNotFound: in case the network is not found.
        """
        try:
            return self.client.networks.get(name)
        except docker.errors.NotFound:
            raise exceptions.NetworkNotFound

    def createService(self,
                      image_name,
                      name=None,
                      hostname=None,
                      env=None,
                      ports=None,
                      mounts=None,
                      should_always_restart=False,
                      restart_max_attempts=0,
                      is_service_global=True,
                      num_of_replicas=1,
                      networks=None):
        """
        Create a service - run an image in an "operational" mode.

        A service runs a given image in a given number of containers, while setting its network, mounts,  
        action in case of restart, etc.

        :param image_name: the image to create the containers from.
        :param name: The name of the service.
        :param hostname: the hostname containers should have.
        :param env: environment variables in the form of ["key1=val1", "key2=val2"]
        :param ports: Exposed ports that this service is accessible on from the outside, in the form of 
            { target_port: published_port } or { target_port: (published_port, protocol) }
        :param mounts: Mounts for the containers, in the form source:target:options, where options is either ro or rw.
        :param should_always_restart: If True, a container that exists will be immediately restarted up to 
            restart_max_attempts. Defaults to True.
        :param restart_max_attempts: defaults to 0, which is unlimited. if should_always_restart is True then this is 
            the max attempts to restart a container before giving up. 
        :param is_service_global: defaults to True. If true, the service is going to be global and not replicated. 
        :param num_of_replicas: defaults to 1. If is_service_global is False, we set the mode to "replicated" and set up
            this number of replicas.

        :type image_name: str
        :type name: str
        :type hostname: str
        :type env: list of str
        :type ports: dict
        :type mounts: list of str
        :type should_always_restart: boolean
        :type restart_max_attempts: int
        :type is_service_global: boolean
        :type num_of_replicas: int
        :raises docker.errors.APIError: in case of an error from the docker server.
        :returns: The service object created.
        :rtype: Service

        .. note:: We have to create a swarm and be the swarm managers. This is done using :py:func:`initSwarm`.
        """

        kwargs = {}
        if name is not None:
            kwargs["name"] = name

        if hostname is not None:
            kwargs["hostname"] = hostname

        if env is not None:
            kwargs["env"] = env

        if ports is not None:
            es = docker.types.EndpointSpec(ports=ports)
            kwargs["endpoint_spec"] = es

        if mounts is not None:
            kwargs["mounts"] = mounts

        if should_always_restart is True:
            rp = docker.types.RestartPolicy(
                condition="any", max_attempts=restart_max_attempts)
            kwargs["restart_policy"] = rp

        if is_service_global is True:
            sm = docker.types.ServiceMode("global")
        else:
            sm = docker.types.ServiceMode(
                "replicated", replicas=num_of_replicas)
        kwargs["mode"] = sm

        if networks is not None:
            kwargs["networks"] = networks

        # docker stop sends s SIGTERM, and only afterwards it sends a SIGKILL.
        kwargs["stop_grace_period"] = 60

        return self.client.services.create(image=image_name, **kwargs)

    def removeService(self, service_name):
        """
        Remove a given service.

        :param str service_name: The service name to remove.
        :raise dockermanager.exceptions.ServiceNotFound: In case the service was not found.
        """
        try:
            service = self.client.services.get(service_name)
        except docker.errors.NotFound:
            raise exceptions.ServiceNotFound(
                "Service %s not found. " % (service_name, ))

        return service.remove()

    def getService(self, service_name):
        """
        Remove a given service.

        :param str service_name: The service name to remove.
        :raise dockermanager.exceptions.ServiceNotFound: in case the service was not found.
        """

        try:
            return self.client.services.get(service_name)
        except docker.errors.NotFound:
            raise exceptions.ServiceNotFound(
                "Service %s not found. " % (service_name, ))

    def getImage(self, image_name):
        """
        Get a docker image currently loaded on this machine.

        :param str image_name: The image name.
        :raise dockermanager.exceptions.ImageNotFound: in case there is no such image.
        :return: The image.
        """

        try:
            return self.client.images.get(image_name)
        except docker.errors.NotFound:
            raise exceptions.ImageNotFound

    def getImagesList(self):
        """Return a list of all loaded images on this machine."""
        return self.client.images.list()

    def isServiceExists(self, service_name):
        """
        Check if service exists.

        :param str service_name: the service name to check for existance.
        :return: True if exists, false otherwise.def
        """

        try:
            self.client.services.get(service_name)
            return True
        except docker.errors.NotFound:
            return False

    def getServicesList(self):
        """Return a list of all services on this machine."""
        return self.client.services.list()

    def loadImage(self, image_path):
        """Load an image from a path. The image should be a tar file created by docker.save."""
        with open(image_path, "rb") as f:
            return self.client.load(f.read())
