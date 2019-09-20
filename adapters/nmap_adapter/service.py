import datetime
import logging
import urllib
import xml.etree.ElementTree as ET
import requests
import chardet
# pylint: disable=import-error
from smb.SMBHandler import SMBHandler

from axonius.adapter_base import AdapterProperty
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.parsing import is_domain_valid
from axonius.devices.device_adapter import DeviceAdapter
from axonius.clients.rest.consts import get_default_timeout
from axonius.smart_json_class import SmartJsonClass
from axonius.fields import Field, ListField
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.files import get_local_config_file
from axonius.utils.xml2json_parser import Xml2Json


logger = logging.getLogger(f'axonius.{__name__}')


class ScriptInformation(SmartJsonClass):
    script_id = Field(str, 'Script Id')
    script_output = Field(str, 'Script Output')


class NmapPortInfo(SmartJsonClass):
    protocol = Field(str, 'Protocol')
    portid = Field(str, 'Port Id')
    state = Field(str, 'State')
    reason = Field(str, 'Reason')
    service_name = Field(str, 'Service Name')
    service_product = Field(str, 'Service Product')
    service_method = Field(str, 'Service Method')
    service_conf = Field(str, 'Service Configuration')
    service_extra_info = Field(str, 'Service Extra Info')
    cpe = Field(str, 'cpe')
    script_information = ListField(ScriptInformation, 'Script Information')


class NmapAdapter(ScannerAdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        file_name = Field(str, 'Nmap File Name')
        start_time = Field(datetime.datetime, 'Start Time')
        end_time = Field(datetime.datetime, 'End Time')
        ports_info = ListField(NmapPortInfo, 'Ports Information')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return client_config['user_id']

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        if not client_config.get('nmap_http') and 'nmap_file' not in client_config \
                and not client_config.get('nmap_share'):
            raise ClientConnectionException('Bad params. No File or URL or Share for nmap')
        self.create_nmap_info_from_client_config(client_config)
        return client_config

    def create_nmap_info_from_client_config(self, client_config):
        nmap_data_bytes = None
        if client_config.get('nmap_http'):
            try:
                nmap_data_bytes = requests.get(client_config.get('nmap_http'),
                                               verify=False,
                                               timeout=get_default_timeout()).content
            except Exception:
                logger.exception(f'Couldn\'t get nmap info from URL')
        elif client_config.get('nmap_share'):
            try:
                share_username = client_config.get('nmap_share_username')
                share_password = client_config.get('nmap_share_password')
                if not share_password or not share_username:
                    share_password = None
                    share_username = None
                share_path = client_config.get('nmap_share')
                if not share_path.startswith('\\\\'):
                    raise Exception('Bad Share Format')
                share_path = share_path[2:]
                share_path = share_path.replace('\\', '/')
                if share_username and share_password:
                    share_path = f'{urllib.parse.quote(share_username)}:' \
                                 f'{urllib.parse.quote(share_password)}@{share_path}'
                share_path = 'smb://' + share_path
                opener = urllib.request.build_opener(SMBHandler)
                with opener.open(share_path) as fh:
                    nmap_data_bytes = fh.read()
            except Exception:
                logger.exception(f'Couldn\'t get nmap info from share')
        elif 'nmap_file' in client_config:
            nmap_data_bytes = self._grab_file_contents(client_config['nmap_file'])
        if nmap_data_bytes is None:
            raise Exception('Bad Nmap, could not parse the data')
        encoding = chardet.detect(nmap_data_bytes)['encoding']  # detect decoding automatically
        encoding = encoding or 'utf-8'
        nmap_data = nmap_data_bytes.decode(encoding)
        nmap_xml = ET.fromstring(nmap_data)
        if not 'nmaprun' in nmap_xml.tag:
            raise Exception(f'Bad Nmap XML, basic tag is {nmap_xml}')
        return nmap_xml, client_config['user_id']

    def _query_devices_by_client(self, client_name, client_data):
        return self.create_nmap_info_from_client_config(client_data)

    @staticmethod
    def _clients_schema():
        return {
            'items': [
                {
                    'name': 'user_id',
                    'title': 'Nmap File Name',
                    'type': 'string'
                },
                {
                    'name': 'nmap_file',
                    'title': 'Nmap XML File',
                    'description': 'The binary contents of the Nmap XML File',
                    'type': 'file'
                },
                {
                    'name': 'nmap_http',
                    'title': 'Nmap XML URL Path',
                    'type': 'string'
                },
                {
                    'name': 'nmap_share',
                    'title': 'Nmap XML Share Path',
                    'type': 'string'
                },
                {
                    'name': 'nmap_share_username',
                    'title': 'Nmap Share User Name',
                    'type': 'string'
                },
                {
                    'name': 'nmap_share_password',
                    'title': 'Nmap Share Password',
                    'type': 'string',
                    'format': 'password'
                },
            ],
            'required': [
                'user_id',
            ],
            'type': 'array'
        }

    @staticmethod
    def _add_port_info(device, port_xml):
        port_info = NmapPortInfo()
        port_info.protocol = port_xml.attrib.get('protocol')
        port_info.portid = port_xml.attrib.get('portid')
        for port_xml_property in port_xml:
            try:
                if port_xml_property.tag == 'service':
                    port_info.service_name = port_xml_property.attrib.get('name')
                    port_info.service_product = port_xml_property.attrib.get('product')
                    port_info.service_method = port_xml_property.attrib.get('method')
                    port_info.service_conf = port_xml_property.attrib.get('conf')
                    device.figure_os(port_xml_property.attrib.get('ostype'))
                    port_info.service_extra_info = port_xml_property.attrib.get('extrainfo')
                    try:
                        if port_xml_property[0].tag == 'cpe':
                            port_info.cpe = port_xml_property[0].text
                    except Exception:
                        pass
                elif port_xml_property.tag == 'state':
                    port_info.state = port_xml_property.attrib.get('state')
                    port_info.reason = port_xml_property.attrib.get('reason')
                elif port_xml_property.tag == 'script':
                    try:
                        script_id = port_xml_property.attrib.get('id')
                        script_output = port_xml_property.attrib.get('output')
                        if script_id and script_output:
                            port_info.script_information.append(ScriptInformation(script_id=script_id,
                                                                                  script_output=script_output))
                    except Exception:
                        logger.exception(f'Problem with scripts')
            except Exception:
                logger.exception(f'Problem getting port info service')
        device.ports_info.append(port_info)

    @staticmethod
    def _parse_host_script(device, host_xml):
        for xml_elem in host_xml:
            try:
                if xml_elem.tag == 'elem':
                    if xml_elem.attrib.get('key') == 'server' and xml_elem.text:
                        device.hostname = xml_elem.text.strip('\\x00')
                        device.id += '_' + xml_elem.text.strip('\\x00')
                    elif xml_elem.attrib.get('key') == 'domain':
                        domain = xml_elem.text.strip('\\x00')
                        if is_domain_valid(domain):
                            device.domain = domain
            except Exception:
                logger.exception(f'Problem with xml elem')

    @staticmethod
    def _parse_nbstat(device, host_xml):
        for xml_elem in host_xml:
            try:
                if xml_elem.tag == 'table' and xml_elem.attrib.get('key') == 'mac':
                    for xml_inner_elem in xml_elem:
                        if xml_inner_elem.tag == 'elem' and xml_inner_elem.attrib.get('key') == 'address'\
                                and xml_inner_elem.text != '<unknown>':
                            device.add_nic(mac=xml_inner_elem.text)
                            device.id += '_' + xml_inner_elem.text
                elif xml_elem.tag == 'elem' and xml_elem.attrib.get('key') == 'server_name':
                    try:
                        device.hostname
                    except Exception:
                        device.hostname = xml_elem.text
            except Exception:
                logger.exception(f'Problem with xml elem')

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks, arguments-differ
    def _parse_raw_data(self, devices_raw_data_full):
        devices_raw_data, file_name = devices_raw_data_full
        for xml_device_raw in devices_raw_data:
            try:
                if xml_device_raw.tag != 'host':
                    continue
                device = self._new_device_adapter()
                device.file_name = file_name
                try:
                    if xml_device_raw.attrib.get('starttime'):
                        device.start_time = datetime.datetime.fromtimestamp(int(xml_device_raw.attrib.get('starttime')))
                except Exception:
                    logger.exception(f'Problem getting start time')
                try:
                    if xml_device_raw.attrib.get('endtime'):
                        device.end_time = datetime.datetime.fromtimestamp(int(xml_device_raw.attrib.get('endtime')))
                except Exception:
                    logger.exception(f'Problem getting end time')
                for xml_property in xml_device_raw:
                    try:
                        if xml_property.tag == 'address':
                            if xml_property.attrib.get('addr'):
                                device.add_nic(ips=xml_property.attrib.get('addr').split(','))
                                device.id = xml_property.attrib.get('addr')
                        elif xml_property.tag == 'ports':
                            try:
                                for xml_port in xml_property:
                                    if xml_port.tag == 'port':
                                        self._add_port_info(device, xml_port)
                                        for xml_port_property in xml_port:
                                            try:
                                                if xml_port_property.tag == 'service':
                                                    service_name_ = (xml_port_property.attrib.get('name'))
                                                    device.add_open_port(protocol=xml_port.attrib.get('protocol'),
                                                                         port_id=xml_port.attrib.get('portid'),
                                                                         service_name=service_name_)
                                            except Exception:
                                                logger.exception(f'Could not add port for xml_port {xml_port}')
                            except Exception:
                                logger.exception(f'Could not add port for xml property {xml_property}')
                        elif xml_property.tag == 'hostscript':
                            for xml_script in xml_property:
                                if xml_script.tag == 'script' and xml_script.attrib.get('id') == 'smb-os-discovery':
                                    self._parse_host_script(device, xml_script)
                                elif xml_script.tag == 'script' and xml_script.attrib.get('id') == 'nbstat':
                                    self._parse_nbstat(device, xml_script)
                    except Exception:
                        logger.exception(f'Problem with property')
                try:
                    device.set_raw(Xml2Json(xml_device_raw).result)
                except Exception:
                    logger.exception(f'Problem setting raw xml device')
                yield device
            except Exception:
                logger.exception(f'Problem adding device')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
