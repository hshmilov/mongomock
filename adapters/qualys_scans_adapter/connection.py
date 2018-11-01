import logging
import xml.etree.cElementTree as ET


from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.xml2json_parser import Xml2Json
from qualys_scans_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')
'''
In this connection we target the VM module (and probably PC later on).
These modules have a rate limit - by default of 2 connections through api v2.0 or 300 api requests an hour.
For the sake of the user - if the next api request is allowed within the next 30 seconds we wait and try again.
'''


class QualysScansConnection(RESTConnection):

    def __init__(self, *args, **kwargs):
        """ Initializes a connection to Illusive using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Illusive
        """
        super().__init__(*args, **kwargs)
        self._permanent_headers = {'X-Requested-With': 'Axonius Qualys Scans Adapter',
                                   'Accept': 'application/json'}

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        response = self._get(consts.SCANS_URL_PREFIX + 'scan', do_basic_auth=True, use_json_in_response=False,
                             url_params=[('action', 'list'),
                                         ('launched_after_datetime',
                                          '3999-12-31T23:12:00Z')])
        response_tree = ET.fromstring(response)
        if response_tree.find('RESPONSE') is None or response_tree.find('RESPONSE').find('DATETIME') is None \
                or response_tree.find('RESPONSE').find('CODE') is not None:
            logger.error(f'Failed to connect to qualys scans. got {response}')
            raise RESTException(f'Got bad XML: {response[:100]}')

    def _get_device_agent_list(self):
        last_id = 0
        has_more_records = 'true'
        pages_count = 0
        while has_more_records == 'true':
            logger.info(f'Got {pages_count * consts.DEVICES_PER_PAGE} devices so far')
            pages_count += 1
            current_iterator_data = consts.QUALYS_SCANS_ITERATOR_FORMAT.format(last_id, consts.DEVICES_PER_PAGE)
            current_clients_page = self._post('qps/rest/2.0/search/am/hostasset/',
                                              do_basic_auth=True,
                                              use_json_in_body=False,
                                              body_params=current_iterator_data)['ServiceResponse']
            yield from current_clients_page['data']
            last_id = current_clients_page.get('lastId')
            has_more_records = current_clients_page['hasMoreRecords']
            if last_id is None and has_more_records == 'true':
                break

    def _get_qualys_scan_results(self, url, url_params, output_key):
        devices_page_count = 0
        while url_params:
            try:
                logger.info(f'Got {devices_page_count*consts.DEVICES_PER_PAGE} devices so far')
                devices_page_count += 1
                response = self._get(consts.SCANS_URL_PREFIX + url + '?' + url_params,
                                     do_basic_auth=True,
                                     use_json_in_response=False)
                current_clients_page = Xml2Json(response).result
                # if there's no response field - there are no clients
                response_json = current_clients_page[output_key]['RESPONSE']
                hosts = response_json.get('HOST_LIST', {}).get('HOST')
                if isinstance(hosts, dict):
                    yield hosts
                if isinstance(hosts, list):
                    yield from hosts
                url_params = ((response_json.get('WARNING') or {}).get('URL') or '?').split('?')[1]
            except Exception:
                logger.exception(f'No devices found for params {url_params}')
                break

    def _get_device_scans_list(self):
        """
        Get all devices from a specific QualysScans domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a QualysScans connection

        :return: A json with all the attributes returned from the QualysScans Server
        """
        logger.info(f'Getting all qualys scannable hosts')
        all_hosts = dict()
        for device_raw in self._get_qualys_scan_results(url=consts.ALL_HOSTS_URL,
                                                        url_params=consts.ALL_HOSTS_PARAMS,
                                                        output_key=consts.ALL_HOSTS_OUTPUT):
            try:
                device_id = device_raw.get('ID')
                if not device_id:
                    logger.warning(f'Bad device without id {str(device_raw)}')
                    continue
                all_hosts[device_id] = device_raw
            except Exception:
                logger.exception(f'Problem getting ID for {str(device_raw)}')
        logger.info(f'Getting all vulnerable hosts')
        try:
            vm_hosts = self._get_qualys_scan_results(url=consts.VM_HOST_URL,
                                                     url_params=consts.VM_HOST_PARAMS,
                                                     output_key=consts.VM_HOST_OUTPUT)
        except Exception:
            logger.exception(f'Problem getting detection lists')
            vm_hosts = []

        for device_raw in vm_hosts:
            try:
                if not device_raw.get('ID'):
                    logger.warning(f'Bad device without id {str(device_raw)}')
                    continue
                if device_raw['ID'] in all_hosts:
                    all_hosts[device_raw['ID']]['DETECTION_LIST'] = device_raw.get('DETECTION_LIST') or {}
                else:
                    all_hosts[device_raw['ID']] = device_raw
            except Exception:
                logger.exception(f'Problem add detection list to {device_raw}')
        yield from all_hosts.values()

    def get_device_list(self):
        try:
            for device_raw in self._get_device_agent_list():
                yield device_raw, consts.AGENT_DEVICE
        except Exception:
            logger.exception(f'Problem getting agents moving to scans')
        # No try except needed here
        for device_raw in self._get_device_scans_list():
            yield device_raw, consts.SCAN_DEVICE
