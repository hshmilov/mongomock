#!/usr/bin/env python3
import logging
from collections import defaultdict

# pylint: disable=import-error
from openstack.connection import Connection

from axonius.adapter_exceptions import ClientConnectionException

logger = logging.getLogger(f'axonius.{__name__}')


class OpenstackException(Exception):
    pass


class OpenStackClient:
    def __init__(self, auth_url, username, password, project,  domain='default'):
        self._auth_url = auth_url
        self._username = username
        self._password = password
        self._project = project
        self._domain = domain

        self._sess = None

    def connect(self):
        """
        Open session using the given creds.
        call authorize to check that the we authenticated successfully.
        """
        logger.info('Creating session')
        self._sess = Connection(auth_url=self._auth_url, project_name=self._project,
                                username=self._username, password=self._password, default_domain_name=self._domain)
        try:
            self._sess.authorize()
        except Exception as e:
            raise ClientConnectionException(str(e))

    def get_devices(self):
        """
        Get device list using Openstack's api.
        Requires active session.
        :return: json that contains a list of the devices
        """
        # Check that self.connect() called
        if self._sess is None:
            raise OpenstackException('Unable to get instace list without session')

        return map(lambda x: x.to_dict(), self._sess.compute.servers(all_tenants=True))

    def get_flavor(self, device):
        """
        Get flavor by device json
        Requires active session.
        :return: json that contains the flavor
        """
        flavor = device.get('flavor', {})

        # If we have flavor (not empty dict)
        if flavor:
            flavor = self._sess.compute.get_flavor(flavor['id']).to_dict()
        return flavor

    def get_image(self, device):
        """
        get image by device json
        Requires active session.
        :return: json that contains the image
        """
        image = device.get('image', {})

        # If we have image (not empty dict)
        if image:
            image = self._sess.compute.get_image(image['id']).to_dict()
        return image

    @staticmethod
    def get_nics(device):
        """
        Extract mac, list(ips) from device json
        :return: json that conatins the ifaces
        """

        result = defaultdict(list)
        for networks in device['addresses'].values():
            for network in networks:
                result[network['OS-EXT-IPS-MAC:mac_addr']].append(network['addr'])
        return result

    def disconnect(self):
        """
        close session
        """
        self._sess = None
