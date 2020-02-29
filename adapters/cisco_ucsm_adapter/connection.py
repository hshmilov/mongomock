import logging

from ucsmsdk.ucshandle import UcsHandle

from cisco_ucsm_adapter.consts import CLSIDS
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException


logger = logging.getLogger(f'axonius.{__name__}')


class CiscoUcsmConnection(RESTConnection):
    """ rest client for CiscoUcsm adapter """

    def __init__(self, *args, secure: bool = None, proxy: str = None, **kwargs):
        self._proxy = proxy
        self._secure = bool(secure)  # Converts None into False (and generally uses truthiness)
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._ucshandle = UcsHandle(self._domain, self._username, self._password, self._port, self._secure, self._proxy)

    def _connect(self):
        try:
            success = self._ucshandle.login(auto_refresh=True)
        except Exception as ex:
            message = f'Could not authenticate {self._domain} with {self._username}: {str(ex)}'
            logger.exception(message)
            raise RESTException(message)
        if not success:
            message = f'Could not authenticate {self._domain} with {self._username}!'
            raise RESTException(message)
        self._session = self._ucshandle
        return success

    def connect(self):
        """
        UCSM connection uses its own connection manager. See ucsmsdk.ucshandle and
        ucsmsdk.ucssession
        """
        self.revalidate_session_timeout()
        self.check_for_collision_safe()
        self._validate_no_connection()
        return self._connect()

    def close(self):
        """ Close the connection """
        if self._session is not None:
            self._session.logout()
            self._session = None
        self._session_headers = {}

    def __del__(self):
        self._ucshandle = None
        super().__del__()

    def get_device_list(self):
        devices_raw_dict = dict()
        try:
            response = self._session.query_classids(
                CLSIDS['blade'],
                CLSIDS['switch'],
                CLSIDS['rack'],
            )
        except Exception as ex:
            message = f'Failed to fetch devices: {str(ex)}'
            logger.exception(message)
            raise

        device_lists = response.values()
        devices_raw = list()
        for dev_list in device_lists:
            devices_raw.extend(dev_list)
        for device_obj in devices_raw:
            devices_raw_dict[device_obj.dn] = device_obj.__json__()
            try:
                if device_obj.get_class_id() == CLSIDS['switch']:
                    continue
            except Exception as ex:
                message = f'Failed to fetch device class_id: {str(ex)}'
                logger.warning(message, exc_info=True)
                continue
            device_props = {
                'cpus': self._get_device_cpus(device_obj),
                'vics': self._get_device_vics(device_obj),
                'disks': self._get_device_disks(device_obj),
            }
            devices_raw_dict[device_obj.dn]['ax_props'] = device_props
        yield from devices_raw_dict.values()

    def _get_device_cpus(self, device_obj):
        try:
            cpus_raw = self._session.query_children(in_dn=device_obj.dn + '/board',
                                                    class_id=CLSIDS['cpu'])
        except Exception as ex:
            message = f'Failed to fetch device cpus: {str(ex)}'
            logger.warning(message, exc_info=True)
            return []
        else:
            return [cpu.__json__() for cpu in cpus_raw]

    def _get_device_vics(self, device_obj):
        try:
            vics_raw = self._session.query_children(in_dn=device_obj.dn, class_id=CLSIDS['vic'])
        except Exception as ex:
            message = f'Failed to fetch device vics: {str(ex)}'
            logger.warning(message, exc_info=True)
            return []
        else:
            return [vic.__json__() for vic in vics_raw]

    def _get_device_disks(self, device_obj):
        disks = list()
        try:
            storage_controllers = self._session.query_children(in_dn=device_obj.dn + '/board',
                                                               class_id=CLSIDS['storage'])
        except Exception as ex:
            message = f'Failed to fetch device disks: {str(ex)}'
            logger.warning(message, exc_info=True)
            return disks
        for stctl in storage_controllers:
            try:
                disks_raw = self._session.query_children(in_mo=stctl, class_id=CLSIDS['disk'])
                disks.extend([disk.__json__() for disk in disks_raw])
            except Exception as ex:
                message = f'Failed to fetch device disk details for {stctl.__json__()}: {str(ex)}'
                logger.warning(message, exc_info=True)
                continue
        return disks
