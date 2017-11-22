#!/usr/bin/env python3
"""This is the main script in which we initialize the core component."""
import sys
import argparse
import environmentmanager


def service_start(em, args):
    """
    Start a service.

    :param args: an object containing args from the command line (supplied by ArgumentParser).
        gets args.service_image (service image to start) and args.service_name (the name of the service)
    """
    service_image = args.service_image
    service_name = args.service_name
    extra_mounts = []

    # Check the mount validity
    if args.mount is not None:
        try:
            (host, dest, mode) = args.mount.split(":")
            if mode not in ("rw", "ro"):
                raise ValueError()
            extra_mounts.append(args.mount)
        except ValueError:
            print("Illegal mount format!")
            return

    if not service_image.startswith("axonius/"):
        print(
            "service image name should be in the form of repostiory/name, e.g. axonius/core")

    # If we don't have a specific service name, make one.
    if service_name is None:
        # Creating name. For example, axonius/core becomes axonius_core
        service_name = '_'.join(service_image.split("/"))

    print("Starting %s as %s..." % (service_image, service_name))

    try:
        em.startService(service_image, service_name, extra_mounts=extra_mounts)
    except environmentmanager.exceptions.ServiceAlreadyRunning:
        print("%s is already running." % (service_name, ))
        return
    except environmentmanager.exceptions.ServiceNotFound:
        print("Can't find %s. Try these: " % (service_name, ))
        images_list = em.dm.getImagesList()

        for im in images_list:
            im_tags_str = ""
            for t in im.tags:
                if t.startswith("axonius/"):
                    im_tags_str += "%s " % (t, )

            if im_tags_str != "":
                print("\t%s" % (im_tags_str, ))

        return

    print("%s started successfully as %s." % (service_image, service_name))


def service_stop(em, args):
    """
    Stop a service.

    :param args: an object containing args from the command line (supplied by ArgumentParser)
        gets args.service_name - the name of the service to stop.
    """

    service_name = args.service_name

    print("Stopping %s..." % (service_name, ))
    try:
        em.stopService(service_name)
    except environmentmanager.exceptions.ServiceNotFound:
        print("%s is not running." % (service_name, ))
        return

    print("%s stopped successfully." % (service_name, ))


def system_status(em, args):
    """
    Print a status.

    :param args: an object containing args from the command line (supplied by ArgumentParser)
    """

    print(em)


def service_load(em, args):
    """
    Load a new service image into the system.

    :param args: an object containing args from the command line (supplied by ArgumentParser)
        args.image_path should be a path to a tar file containing docker image.
    """

    print("Loading %s.." % (args.image_path, ))
    em.loadService(args.image_path)
    print("Service loaded successfully.")


def main():
    """Parse arguments and control services."""

    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers()

    sp_start = subparser.add_parser(
        'start', help='Starts a service. type -h for help')
    sp_start.add_argument('-i', default='axonius/core', help='The service image to start. default: axonius/core',
                          dest="service_image")
    sp_start.add_argument('-n', default=None, help='The service name. default: repository_name, e.g. axonius_core',
                          dest="service_name")
    sp_start.add_argument('--mount', default=None,
                          help='An optional mount to to have in the form of "host:guest:mode", \
                          e.g. "/mnt/hgfs/C/temp:/app:rw" ', dest="mount")
    sp_start.set_defaults(which=service_start)

    sp_stop = subparser.add_parser(
        'stop', help='Stops a service. type -h for help')
    sp_stop.add_argument('-n', default='axonius_core', help='The service name to stop. default: axonius_core',
                         dest="service_name")
    sp_stop.set_defaults(which=service_stop)

    sp_load = subparser.add_parser(
        'load', help='Loads a new service image into the system')
    sp_load.add_argument('-n', help='The image (tar file) path.',
                         dest="image_path")
    sp_load.set_defaults(which=service_load)

    sp_status = subparser.add_parser(
        'status', help='Prints a status of the axonius system')
    sp_status.set_defaults(which=system_status)

    args = parser.parse_args()

    if not hasattr(args, 'which'):
        parser.print_help()
        return

    em = environmentmanager.EnvironmentManager()

    args.which(em, args)


if __name__ == '__main__':
    sys.exit(main())
