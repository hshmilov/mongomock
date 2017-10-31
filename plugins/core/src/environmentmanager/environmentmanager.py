"""
Manages plugins that are hosted on the core machine in isolated environments.

Plugins (including the core) that intend being hosted on the current server
should be in an isolated environment of their own.
"""
from . import dockermanager
from . import exceptions
from . import config
import os

__author__ = "Avidor Bartov"


class EnvironmentManager(object):
    """Manages isolated environments to run the core and plugins which are to be hosted in this server."""

    def __init__(self):
        """Initialize the Environment manager."""
        self.dm = dockermanager.DockerManager()
        
        # initialize our state.
        self.initializeEnvironment()
        self.updateStateFromEnv()

    def __str__(self):
        """Return a string representing all services, tasks and their status."""

        services_to_print = self.services

        string_to_return = "There are %d services running: \n" % (len(services_to_print))

        for s in services_to_print:
            string_to_return += "\n"
            string_to_return += "Image: %s, Name: %s(%s)\n" % \
                (s.attrs["Spec"]["TaskTemplate"]["ContainerSpec"]["Image"],
                 s.name, 
                 s.short_id)
            for t in s.tasks():
                # Sometimes, some containers fail to load.
                container_id = "Unknown"
                state = "Unknown"
                message = "Unknown"

                try:
                    container_id = t["Status"]["ContainerStatus"]["ContainerID"][:8]
                except KeyError:
                    pass

                try:
                    state = t["Status"]["State"]
                except KeyError:
                    pass

                try:
                    message = t["Status"]["Message"]
                except KeyError:
                    pass

                string_to_return += "\tContainer: %s, State: %s, Message: %s\n" % \
                    (container_id, 
                     state, 
                     message)

                for network in t["NetworksAttachments"]:
                    string_to_return += "\t\tIP: "
                    for ip in network["Addresses"]:
                        string_to_return += "%s " % (ip, )
                    
                string_to_return += "\n"

        return string_to_return

    def initializeEnvironment(self):
        """Initialize the environment. Basically this means create a network, and initialize a swarm."""
        self.dm.initSwarm()
        try:
            self.network = self.dm.getNetwork(config.NETWORK_NAME)
        except dockermanager.exceptions.NetworkNotFound:
            self.network = self.dm.createNetwork(config.NETWORK_NAME)

    def updateStateFromEnv(self):
        """
        Use the docker current running services and tasks to understand what is going on.

        .. todo:: Once we have a database - change that. Environments should be connected to registered services.
        """

        self.services = self.getServicesList()

        try:
            self.core = self.dm.getService(config.CORE_SERVICE_NAME)
        except dockermanager.exceptions.ServiceNotFound:
            self.core = None

    def getServicesList(self):
        """Get a list of all services currently running on the system. Each one starting with our prefix is ours.

        :return list: The list of services running.

        .. todo:: Once we have a db, the state should be set by the DB state.
        """

        services_list_to_return = self.dm.getServicesList()        

        for s in services_list_to_return:
            if s.name.startswith(config.SERVICE_PREFIX) is False:
                services_list_to_return.remove(s)

        return services_list_to_return

    def startService(self, image_name, service_name, extra_mounts=[]):
        """
        Start a new service by its id or name.

        When we run a set of plugins, we actually run a service that runs 1 or a couple of containers, All of which
        have the same volume mapped usually to "/storage". If one of the containers fail, the service is configured
        to auto-reload them.

        :param str image_name: The image name to start. In the form of repository/name.
        :param str service_name: The service name to start. In the form of prefix_some_service_name.
        :param extra_mounts: A list of strings representing extra mounts to do, in the form of 
            "host_path:container_path:mode". mode should be "ro" or "rw". 
        :type extra_mounts: list of strings
        :raise environmentmanager.exceptions.IllegalImageName: In case the image name given is illegal.
        :raise environmentmanager.exceptions.ServiceAlreadyRunning: In case the service is already running.
        """

        # Imagename should always follow the convention of "repository/name".
        if not image_name.startswith("axonius/"):
            raise exceptions.IllegalImageName(
                "Image name should always follow the convention of repository/name, e.g. axonius/core")

        if not service_name.startswith("axonius_"):
            raise exceptions.IllegalServiceName(
                "Service name should always follow the convention of repository_name, e.g. axonius_core")

        if self.dm.isServiceExists(service_name):
            raise exceptions.ServiceAlreadyRunning("Service %s already running." % (service_name, ))

        # Check if we have such image in the system.
        try:
            self.dm.getImage(image_name)
        except dockermanager.exceptions.ImageNotFound:
            raise exceptions.ServiceNotFound

        # Prepare the service parameters
        kwargs = {}
        kwargs["env"] = []
        kwargs["should_always_restart"] = True
        kwargs["networks"] = [config.NETWORK_NAME]  # currently, all services are in the same network.
        # Map containers "/storage" path to "./storage/service_name/data"
        kwargs["mounts"] = ["%s:/storage:rw" % (os.path.join(os.path.abspath("storage"), service_name, 'data'), )]
        # Map containers "/logs" path to "./storage/service_name/logs"
        kwargs["mounts"].append("%s:/logs:rw" % (os.path.join(os.path.abspath("storage"), service_name, 'logs'), ))
        # Add extra mounts
        kwargs["mounts"].extend(extra_mounts)

        if service_name == config.CORE_SERVICE_NAME:
            # We have special parameters for the core. 
            kwargs["ports"] = {config.CORE_EXTERNAL_EXPOSED_PORT: 
                               (config.CORE_INTERNAL_EXPOSED_PORT, "tcp")}
            kwargs["mounts"].extend([
                '/var/run/docker.sock:/var/run/hostdocker.sock:rw',     # This is the host docker socket, so that the 
                                                                        # core container could manage the host
                "%s:/allstorage:rw" % (os.path.abspath("storage"))])    # The storage of all services

        # Prepare the storage
        os.makedirs(os.path.join("storage", service_name, 'data'), exist_ok=True)
        os.makedirs(os.path.join("storage", service_name, 'logs'), exist_ok=True)

        service = self.dm.createService(image_name, service_name, **kwargs)
        self.services.append(service)

        return True

    def stopService(self, service_name):
        """
        Stop a service by its id or name.

        :param str service_name: The service name to stop.
        :raise exceptions.ServiceNotFound: In case the service is not found.
        
        """
        try:
            self.dm.removeService(service_name)
        except dockermanager.exceptions.ServiceNotFound:
            raise exceptions.ServiceNotFound

        if service_name == config.CORE_SERVICE_NAME:
            self.core = None

        return True

    def loadService(self, image_location):
        """
        Load a new service image.

        :param str image_location: The path of the **docker** tar.gz file.
        """
        self.dm.loadImage(image_location)
