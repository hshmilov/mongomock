#!/usr/bin/env python3.6

import argparse
import sys

import docker


def destroy(keep_diag=True, keep_tunnel=True):
    """
    - stops all running containers (can keep some, see flags)
    - remove all containers (can keep some, see flags)
    - *removes all "axonius/" images*
    :param keep_diag: should keep diag (running container and the image)
    :param keep_tunnel: should keep tunnler and weave containers for instance
    host connection(running container and the image)
    """
    client = docker.from_env()
    instances_dockers_container_names_substrings_to_keep = ['tunnler', 'weave', 'grid']
    instances_docker_tag_substring_to_keep = ['socat', 'weave', 'selenium']

    for container in client.containers.list():
        if (keep_diag and container.name == 'diagnostics') or (
                keep_tunnel and [current_container_name for current_container_name in
                                 instances_dockers_container_names_substrings_to_keep if
                                 current_container_name in container.name]):
            print(f'Skipping {container.name}')
            continue

        try:
            print(f'Stopping {container.name}')
            container.stop(timeout=3)
            container.remove(force=True)
        except Exception as e:
            print(f'Error while removing container {container.name}: {e}')

    # remove gui volume
    print(f'Removing gui volume')
    try:
        client.volumes.get('gui_data').remove(force=True)
    except Exception:
        print('gui_data volume not found')

    # docker is a bad boy. If there is some kind of dependency you should try to remove all images twice
    for x in range(1, 5):
        for image in client.images.list():
            tags = ','.join(image.tags)

            if 'ubuntu:trusty' in tags:
                # currently we can't upgrade ubuntu base image because diagnostics relies on it
                print(f'Skipping {image}')
                continue

            # Checking if the current image tags is 'diagnostics' or if any of the tags
            # contain any of the instances_dockers_to_keep as a substring
            cond = [x for x in instances_docker_tag_substring_to_keep if x in tags]
            if (keep_diag and 'diagnostics' in tags) or (keep_tunnel and cond):
                print(f'Skipping {image}')
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
    parser.add_argument('--keep-tunnel', action='store_true', default=True)

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    destroy(keep_diag=args.keep_diag, keep_tunnel=args.keep_tunnel)


if __name__ == '__main__':
    main()
