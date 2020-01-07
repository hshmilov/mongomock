import shutil


def get_free_disk_space():
    """
    Returns the free disk space in bytes. Notice that multiple mounting points can be present,
    so this returns the free disk space for the '/' of the running container. Since this is often a volume,
    it actually returns the number of bytes free on the mount on which the volume docker resides == on which docker
    is mounted.

    Another way to do this outside of a container would be:
    shutil.disk_usage(docker.from_env().info()['DockerRootDir']).free / (1024 ** 3)
    :return:
    """
    return shutil.disk_usage('/').free
