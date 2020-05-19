import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from citrix_epm_adapter.connection import CitrixEpmConnection
from citrix_epm_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class CitrixEpmAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        jailbroken = Field(bool, 'Jailbroken')
        managed = Field(bool, 'Managed')
        gateway_blocked = Field(bool, 'Gateway Blocked')
        deploy_failed = Field(bool, 'Deploy Failed')
        deploy_pending = Field(bool, 'Deploy Pending')
        deploy_success = Field(bool, 'Deploy Successful')
        imei = Field(str, 'IMEI')
        meid = Field(str, 'MEID')
        mdm_known = Field(bool, 'Known to MDM')
        mam_registered = Field(bool, 'Registered in MAM')
        mam_known = Field(bool, 'Known to MAM')
        activesync_id = Field(str, 'ActiveSync ID')
        device_platform = Field(str, 'Device Platform')
        days_inactive = Field(int, 'Days Inactive')
        shareable = Field(bool, 'Shareable')
        shared_status = Field(str, 'Shared Status')
        dep_registered = Field(bool, 'Registered in DEP')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                port=client_config.get('port'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = CitrixEpmConnection(domain=client_config.get('domain'),
                                         port=client_config.get('port'),
                                         verify_ssl=client_config.get('verify_ssl'),
                                         https_proxy=client_config.get('https_proxy'),
                                         username=client_config.get('username'),
                                         password=client_config.get('password'))
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as err:
            message = f'Error connecting to client with domain ' \
                      f'{client_config["domain"]}, reason: {str(err)}'
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema CitrixEpmAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Citrix Endpoint Management Domain',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'default': 4443,
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'port',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-statements, too-many-branches, too-many-locals, too-many-nested-blocks
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID: {device_raw}')
                return None
            try:
                device.id = str(device_id) + '_' + (device_raw.get('serialNumber') or '')
            except Exception:
                logger.exception(f'Unable to set device ID: {device_id} is type {type(device_id)}')
                raise

            device.name = device_raw.get('deviceName')

            device.device_serial = device_raw.get('serialNumber') or ''

            uid = device_raw.get('imeiOrMeid')
            if isinstance(uid, str):
                device.uuid = uid
                # all IMEIs are 15 or 16 chars, while MEIDs are 14
                if len(uid) > 14:
                    device.imei = uid
                else:
                    device.meid = uid

            # bluetooth mac address typo in docs
            macs = [device_raw.get('wifiMacAddress'),
                    device_raw.get('bluetoothMacAddress')]
            device.add_ips_and_macs(macs=macs)

            device.figure_os(f'{device_raw.get("platform")} '
                             f'{device_raw.get("osVersion")}')

            device.last_seen = parse_date(device_raw.get('lastAccess'))
            device.device_model_family = device_raw.get('deviceType')
            device.device_model = device_raw.get('productName') or device_raw.get('deviceModel')

            jailbroken = device_raw.get('jailBroken')
            if isinstance(jailbroken, bool):
                device.jailbroken = jailbroken

            managed = device_raw.get('managed')
            if isinstance(managed, bool):
                device.managed = managed

            blocked = device_raw.get('gatewayBlocked')
            if isinstance(blocked, bool):
                device.gateway_blocked = blocked

            # unsure of data type due to poor documentation
            failed = device_raw.get('deployFailed')
            if isinstance(failed, int):
                device.deploy_failed = bool(failed)

            # unsure of data type due to poor documentation
            pending = device_raw.get('deployPending')
            if isinstance(pending, int):
                device.deploy_pending = bool(pending)

            # unsure of data type due to poor documentation
            success = device_raw.get('deploySuccess')
            if isinstance(success, int):
                device.deploy_success = bool(success)

            mdm_known = device_raw.get('mdmKnown')
            if isinstance(mdm_known, bool):
                device.mdm_known = mdm_known

            mam_registered = device_raw.get('mamRegistered')
            if isinstance(mam_registered, bool):
                device.mam_registered = mam_registered

            mam_known = device_raw.get('mamKnown')
            if isinstance(mam_known, bool):
                device.mam_known = mam_known

            device.activesync_id = device_raw.get('activeSyncId')
            device.device_platform = device_raw.get('devicePlatform')

            inactive = device_raw.get('inactivityDays')
            try:
                if isinstance(inactive, str):
                    device.days_inactive = int(inactive)
            except Exception:
                logger.exception(f'Unable to cast {inactive} to an integer')

            first_name = device_raw.get('userGivenName')
            # there is (potentially) a typo in the documentation so checking for typical spelling too.
            last_name = device_raw.get('userSurnamee') or device_raw.get('userSurname')

            if first_name and last_name:
                device.last_used_users.append(f'{first_name} {last_name}')

            shareable = device_raw.get('shareable')
            if isinstance(shareable, bool):
                device.shareable = shareable

            shared_status = device_raw.get('sharedStatus')
            if isinstance(shared_status, str):
                device.shared_status = shared_status

            dep_registered = device_raw.get('depRegistered')
            if isinstance(dep_registered, bool):
                device.dep_registered = dep_registered

            device_properties = device_raw.get('properties')
            if isinstance(device_properties, list):
                for dev_property in device_properties:
                    if not isinstance(dev_property, dict):
                        continue
                    if not dev_property.get('displayName'):
                        continue
                    key = str(dev_property.get('displayName'))
                    value = dev_property.get('value')
                    # sensitive data check
                    if key != 'Activation lock bypass code':
                        device.add_key_value_tag(key=key,  value=value)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Citrix EPM Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.MDM, AdapterProperty.Manager]
