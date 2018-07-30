#!/usr/bin/env python3

import argparse
import sys

import docker


def destroy(keep_diag=True):
    """
    - stops all running containers (can keep diag)
    - remove all containers (can keep diag)
    - *removes all "axonius/" images*
    - optionally, removes all log files (unless --keep-logs is specified)
    :param keep_diag: should keep diag (running container and the image)
    """
    client = docker.from_env()

    for container in client.containers.list():
        if keep_diag and container.name == 'diagnostics':
            continue

        try:
            print(f'Stopping {container.name}')
            container.stop(timeout=3)
            container.remove()
        except Exception as e:
            print(f'Error while removing container {container.name}: {e}')

    # docker is a bad boy. If there is some kind of dependency you should try to remove all images twice
    for x in range(1, 5):
        for image in client.images.list():
            tags = ','.join(image.tags)

            if 'ubuntu:trusty' in tags:
                # currently we can't upgrade ubuntu base image because diagnostics relies on it
                continue

            if keep_diag and 'diagnostics' in tags:
                continue

            try:
                print(f'Removing {image}')
                client.images.remove(image.id, force=False)
                print(f'Removed {image}')
            except Exception as e:
                print(f'Error while stopping Image {image} {e}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--keep-diag', action='store_true', default=True)

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    destroy(keep_diag=args.keep_diag)


if __name__ == '__main__':
    main()
