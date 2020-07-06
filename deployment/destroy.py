#!/usr/bin/env python3.6

import subprocess
import docker

from utils import print_state


def stop_weave_network():
    try:
        print('Stopping weave network (nodes will reconnect on relaunch).')
        subprocess.check_call('weave stop'.split())
    except subprocess.CalledProcessError:
        print('Failed to stop weave network.')


def destroy():
    """
    - stops all running containers (can keep some)
    - remove all containers (can keep some, see flags)
    - *removes all "axonius/" images*
    host connection(running container and the image)
    """
    client = docker.from_env()
    instances_dockers_container_names_substrings_to_keep = ['grid']
    instances_docker_tag_substring_to_keep = ['selenium']
    stop_weave_network()

    for container in client.containers.list(ignore_removed=True):
        if [current_container_name for current_container_name in instances_dockers_container_names_substrings_to_keep if
                current_container_name in container.name]:
            print(f'Skipping {container.name}')
            continue

        try:
            print(f'Stopping {container.name}')
            container.stop(timeout=600 if container.name == 'mongo' else 3)
            container.remove(force=True)
        except Exception as e:
            print(f'Error while removing container {container.name}: {e}')

    # restart docker service
    print_state(f'Restarting docker service')
    subprocess.check_call('service docker restart'.split())

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

            cond = [x for x in instances_docker_tag_substring_to_keep if x in tags]
            if cond:
                print(f'Skipping {image}')
                continue
            try:
                print(f'Removing {image}')
                client.images.remove(image.id, force=False)
                print(f'Removed {image}')
            except Exception as e:
                print(f'Error while stopping Image {image} {e}')


def main():
    destroy()


if __name__ == '__main__':
    main()
