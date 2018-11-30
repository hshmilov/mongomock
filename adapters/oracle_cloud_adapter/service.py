import datetime
import logging
import oci
from oci.config import validate_config

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.parsing import parse_date
from axonius.utils.files import get_local_config_file
from oracle_cloud_adapter.client_id import get_client_id
from oracle_cloud_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class OracleCloudAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        oci_compartment = Field(str, 'Oracle Cloud Infrastructure Compartment')
        oci_region = Field(str, 'Oracle Cloud Infrastructure Region')
        time_created = Field(datetime.datetime, 'Time Created')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            client_config_copy = client_config.copy()
            file_path = f'{get_client_id(client_config)}_{consts.ORACLE_PRIVATE_KEY_FILE_PATH}'
            file_content = self._grab_file_contents(client_config[consts.ORACLE_KEY_FILE])
            with open(file_path, 'wb') as fd:
                fd.write(file_content)
                fd.flush()
            client_config_copy[consts.ORACLE_KEY_FILE] = file_path
            # First we must validate that the configuration is correct
            validate_config(client_config_copy)
            # There are three kinds of clients that OCI (Oracle Cloud Infrastructure) uses: compute, virtual network,
            # and identity. We must store all three in a dict
            oci_client = dict()
            oci_client['compute_client'] = oci.core.ComputeClient(
                client_config_copy, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
            oci_client['virtual_network_client'] = oci.core.VirtualNetworkClient(
                client_config_copy, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
            oci_client['identity_client'] = oci.identity.IdentityClient(
                client_config_copy, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
            # We will later need the tenancy ocid, so we must save it to the client here
            oci_client['tenancy'] = client_config_copy['tenancy']
            return oci_client
        except Exception as e:
            logger.error('Failed to connect to client %s', self._get_client_id(client_config))
            raise ClientConnectionException(str(e))

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        # Oracle Cloud instances are stored in compartments. We must get a list of all compartments.
        all_compartments = client_data['identity_client'].list_compartments(client_data['tenancy']).data
        for compartment in all_compartments:
            try:
                # Gets a list of all the instances in the current compartment
                all_instances = client_data['compute_client'].list_instances(compartment.compartment_id).data
                for instance_raw in all_instances:
                    try:
                        # This gets general information about the instance (name, id, etc.)
                        instance_general_info = client_data['compute_client'].get_instance(instance_raw.id).data
                        # This gets network information for the instance (ip and mac addresses, etc.)
                        vnic_attachments = oci.pagination.list_call_get_all_results(
                            client_data['compute_client'].list_vnic_attachments,
                            compartment_id=instance_raw.compartment_id,
                            instance_id=instance_raw.id
                        ).data
                        vnics = [client_data['virtual_network_client'].get_vnic(
                            va.vnic_id).data for va in vnic_attachments]
                        raw_device = dict()
                        raw_device['general_info'] = instance_general_info
                        raw_device['network_info'] = vnics
                        yield raw_device
                    except Exception:
                        logger.exception(f'Failed to connect to device: {instance_raw}.')
            except Exception:
                logger.exception(f'Problem with compartment {compartment}')

    @staticmethod
    def _clients_schema():
        """
        The schema OracleCloudAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': consts.ORACLE_CLOUD_USER,
                    'title': 'User OCID',
                    'type': 'string'
                },
                {
                    'name': consts.ORACLE_KEY_FILE,
                    'title': 'Oracle Key File',
                    'type': 'file'
                },
                {
                    'name': consts.ORACLE_FINGERPRINT,
                    'title': 'Key-Pair Fingerprint',
                    'type': 'string'
                },
                {
                    'name': consts.ORACLE_TENANCY,
                    'title': 'Tenancy OCID',
                    'type': 'string'
                },
                {
                    'name': consts.ORACLE_REGION,
                    'title': 'Oracle Cloud Infrastructure Region',
                    'type': 'string'
                },
            ],
            'required': [
                consts.ORACLE_CLOUD_USER,
                consts.ORACLE_KEY_FILE,
                consts.ORACLE_FINGERPRINT,
                consts.ORACLE_TENANCY,
                consts.ORACLE_REGION
            ],
            'type': 'array'
        }

    def create_device(self, device_raw):
        device = self._new_device_adapter()
        try:
            device_id = device_raw['general_info'].id
            if not device_id:
                logger.error(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
        except Exception:
            logger.exception(f'Bad device with no ID {device_raw}')
            return None
        try:
            device.name = device_raw['general_info'].display_name
            device.oci_compartment = device_raw['general_info'].compartment_id
            device.oci_region = device_raw['general_info'].region
        except Exception:
            logger.exception(f'Failed to create general-info device {device_raw}.')
        try:
            device.time_created = parse_date(device_raw['general_info'].time_created)
        except Exception:
            logger.exception(f'Problem adding time created for {device_raw}')

        try:
            if isinstance(device_raw.get('network_info'), list):
                for network_info in device_raw.get('network_info'):
                    try:
                        mac = network_info.mac_address
                        ips = [network_info.public_ip, network_info.private_ip]
                        device.add_nic(ips=ips, mac=mac)
                    except Exception:
                        logger.exception(f'Problem adding network info {str(network_info)}')
        except Exception:
            logger.exception(f'Failed to create network-info device {device_raw}')
        return device

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self.create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
