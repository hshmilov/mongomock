import logging
from collections import defaultdict
from typing import List, Sequence, Tuple

import netaddr

from axonius.utils.datetime import parse_date
from axonius.utils.parsing import is_valid_ip, int_or_none

from axonius.utils.xml2json_parser import Xml2Json

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.consts import remote_file_consts
from axonius.utils import remote_file_utils
from axonius.utils.files import get_local_config_file
from hp_nnmi_xml_adapter.structures import HPNNMIDeviceInstance, ExtendedAttribute, NNMIInterface

logger = logging.getLogger(f'axonius.{__name__}')


class HpNnmiXmlAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(HPNNMIDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return f'HP_NNMI_XML_{client_config["user_id"]}'

    @staticmethod
    def _test_reachability(client_config):
        return remote_file_utils.test_file_reachability(client_config)

    @staticmethod
    def _check_config_section(configs_by_section: dict, section_to_check: str) -> bool:
        """
        Check if the `configs_by_section` has valid data for `section_to_check`
        :param configs_by_section: The complete client_data configs, by section
        :param section_to_check: The section to check (nodes/ips/subnets/interfaces)
        :return: True if the section `section_to_check` is reachable as a file
        """
        try:
            return remote_file_utils.test_file_reachability(configs_by_section.get(section_to_check) or {})
        except Exception as e:
            logger.warning(f'Failed with {str(e)} to check reachability for '
                           f'file, based on {configs_by_section.get(section_to_check)}')
            return False

    def _get_verified_config(self, client_config):
        if self._test_reachability(client_config):  # If True then nodes (primary) is okay
            all_configs = self._get_config_by_section(client_config)
            subnets_available = self._check_config_section(all_configs, 'subnets')
            ips_available = self._check_config_section(all_configs, 'ips')
            interfaces_available = self._check_config_section(all_configs, 'interfaces')
            logger.info(f'Running with files: Nodes'
                        f'{", interfaces" if interfaces_available else ""}'
                        f'{", ips" if ips_available else ""}'
                        f'{", subnets" if subnets_available else ""}.')
            return client_config
        raise ClientConnectionException(f'Failed to load data from {client_config}')

    def _connect_client(self, client_config):
        return self._get_verified_config(client_config)

    @staticmethod
    def _get_config_by_section(client_config: dict):
        all_sections = client_config.copy()
        nodes = {
            'file_path': all_sections.pop('file_path', None),
            'resource_path': all_sections.pop('resource_path', None),
        }
        ips = {
            'file_path': all_sections.pop('file_path_ips', None),
            'resource_path': all_sections.pop('resource_path_ips', None)
        }
        subnets = {
            'file_path': all_sections.pop('file_path_subnets', None),
            'resource_path': all_sections.pop('resource_path_subnets', None)
        }
        interfaces = {
            'file_path': all_sections.pop('file_path_interfaces', None),
            'resource_path': all_sections.pop('resource_path_interfaces', None)
        }
        return {
            'nodes': {**nodes, **all_sections},
            'ips': {**ips, **all_sections},
            'subnets': {**subnets, **all_sections},
            'interfaces': {**interfaces, **all_sections}
        }

    @staticmethod
    def _iter_from_xml(config_section: dict, contents_key='node', top_level='topo') -> List[dict]:
        """
        Load the file described by `config_section`, convert the XML to dict, and return an iterator
        if the xml_dict[top_level][contents_key] (or earlier if one of the above is a list)
        :param config_section:
        :type config_section:
        :param contents_key:
        :type contents_key:
        :param top_level:
        :type top_level:
        :return:
        :rtype:
        """
        if not (config_section and isinstance(config_section, dict)):
            logger.info(f'Config section empty or not a dict: {config_section}')
            return
        file_name, xml_data = remote_file_utils.load_remote_data(config_section)
        xml_json = Xml2Json(xml_data).result
        logger.info(f'Data for {contents_key}s converted to JSON.')
        if isinstance(xml_json, list):
            logger.debug(f'{contents_key} XML json is a list')
            yield from xml_json
        elif isinstance(xml_json, dict):
            logger.debug(f'{contents_key} XML JSON is a dict')
            toplevel = xml_json.get(top_level, {})
            items = toplevel.get(contents_key, toplevel)
            if isinstance(items, list):
                yield from items
            elif isinstance(items, dict):
                yield from [items]
            logger.info(f'Finished iterating from {contents_key}')
        else:
            logger.error(f'Could not load {contents_key} data from XML/JSON {str(xml_json)[:100]}')  # truncate to 100

    # pylint: disable=too-many-branches
    @staticmethod
    def _stack_ifaces_by_node_id(interfaces_iterator: Sequence[dict],
                                 ips_iterator: Sequence[dict],
                                 subnets_iterator: Sequence[dict]) -> Tuple[dict, dict]:
        """
        Get two dicts: interfaces by node id, and orphan_ips by node id
        Orphan IPs are IPs with no interface attached to them
        Interface_by_node_id format:
        { node_id: [
            { **interface_dict, 'x_ips': [  {  **ip_entry,  'x_subnet': {**subnet_entry}, }, ...  ]  }, ...
        ] }
        """
        subnets_by_id = {}
        try:
            for subnet_raw in subnets_iterator:
                if not (isinstance(subnet_raw, dict) and subnet_raw.get('id')):
                    logger.debug(f'Bad subnet: {subnet_raw}')
                    continue
                subnet_id = subnet_raw.get('id')
                subnets_by_id[subnet_id] = subnet_raw
        except Exception as e:
            logger.debug(f'Failed to get subnets_by_id dict, using empty placeholder: {str(e)}')

        orphan_ips_by_node_id = defaultdict(list)
        ips_by_iface_id = defaultdict(list)
        try:
            for ip_raw_dict in ips_iterator:
                if not isinstance(ip_raw_dict, dict):
                    logger.warning(f'Bad ip entry {ip_raw_dict}')
                    continue
                subnet_id = ip_raw_dict.get('subnet')
                ip_raw_dict['x_subnet'] = subnets_by_id.get(subnet_id) or {}
                if ip_raw_dict.get('interface'):
                    ips_by_iface_id[ip_raw_dict.get('interface')].append(ip_raw_dict)
                elif ip_raw_dict.get('node'):
                    orphan_ips_by_node_id[ip_raw_dict.get('node')].append(ip_raw_dict)
                else:
                    logger.warning(f'Invalid IP entry with no correlatable identifiers: {ip_raw_dict}')
        except Exception as e:
            logger.warning(f'Failed to get ips_by_iface_id dict: {str(e)}')

        interfaces_by_node_id = defaultdict(list)
        try:
            for iface_raw in interfaces_iterator:
                if not (isinstance(iface_raw, dict) and iface_raw.get('hostedOnId') and iface_raw.get('id')):
                    logger.warning(f'Bad interface dict {iface_raw}')
                    continue
                iface_id = iface_raw.get('id')
                node_id = iface_raw.get('hostedOnId')
                iface_raw['x_ips'] = ips_by_iface_id.pop(iface_id, [])
                interfaces_by_node_id[node_id].append(iface_raw)
        except Exception as e:
            logger.warning(f'Failed to create interfaces dictionary: {str(e)}')

        # Now if any IPs remain in ips_by_iface_id, they are also orphans
        for orphan_ips in ips_by_iface_id.values():
            for orphan_ip in orphan_ips:
                if not orphan_ip.get('node'):
                    logger.warning(f'Bad IP entry with no correlatable identifiers: {orphan_ip}')
                    continue
                orphan_ips_by_node_id[orphan_ip.get('node')].append(orphan_ip)
        logger.info(f'Finished loading interfaces and IPs')
        return interfaces_by_node_id, orphan_ips_by_node_id

    # pylint: disable=invalid-triple-quote
    @classmethod
    def _iter_nodes(cls, configs_by_section: dict):
        """
        Load all available files, then yield items from the nodes file after attaching all
        relevant entries from the other files, consuming those sub-entries on the fly to keep
        memory footprint manageable.
        Basically, we're creating a dictionary of enriched iface entries, and matching each to the relevant nodes.
        "Enriched" iface_by_node_id dict example in `_stack_ifaces_by_node_id`
        As a result, we yield a node (device_raw) dict, with injected `x_interfaces` item.
        :param configs_by_section: The complete client_data configs, by section
        """
        node_config = configs_by_section.get('nodes')
        # Check each config section and load it if it's good
        interfaces_config = {}
        if cls._check_config_section(configs_by_section, 'interfaces'):
            interfaces_config = configs_by_section.get('interfaces')

        ips_config = {}
        if cls._check_config_section(configs_by_section, 'ips'):
            ips_config = configs_by_section.get('ips')

        subnets_config = {}
        if cls._check_config_section(configs_by_section, 'subnets'):
            subnets_config = configs_by_section.get('subnets')

        # load the primary data file (nodes)
        all_nodes = cls._iter_from_xml(node_config)

        # load secondary data files: IPs, subnets, interfaces, and stack them into a dict
        all_ifaces = cls._iter_from_xml(interfaces_config, 'interface') or []
        all_ips = cls._iter_from_xml(ips_config, 'ip') or []
        all_subnets = cls._iter_from_xml(subnets_config, 'subnet') or []
        ifaces_by_node = {}
        orphan_ips_by_node = {}
        if all_ifaces or all_ips:
            ifaces_by_node, orphan_ips_by_node = cls._stack_ifaces_by_node_id(all_ifaces, all_ips, all_subnets)

        try:
            # Iterate over the nodes, consuming iface entries and injecting them into the node dict
            for node_raw in all_nodes:
                if not (isinstance(node_raw, dict) and node_raw.get('id')):
                    logger.warning(f'Invalid node entry. Expected a dict, got {type(node_raw)}:{str(node_raw)[:100]}')
                    continue
                node_id = node_raw.get('id')
                node_raw['x_ifaces'] = ifaces_by_node.pop(node_id, [])
                node_raw['x_ips'] = orphan_ips_by_node.pop(node_id, [])
                yield node_raw
        except Exception as e:
            logger.exception(f'Error getting devices')
            raise ClientConnectionException(f'Error loading devices: {str(e)}')

    # pylint: disable=invalid-triple-quote
    @classmethod
    def _query_devices_by_client(cls, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        try:
            configs_by_section = cls._get_config_by_section(client_data)
            yield from cls._iter_nodes(configs_by_section)
        except Exception as e:
            logger.exception(f'Error while iterating nodes (devices) for config {client_data}')
            raise ClientConnectionException(f'Error while loading NNMI data from XML: {str(e)}')

    @staticmethod
    def _clients_schema():
        """
        The schema HpNnmiXmlAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                *remote_file_consts.FILE_CLIENTS_SCHEMA,
                {
                    'name': 'file_path_ips',
                    'title': 'Upload IPs XML file',
                    'description': 'Select a file to upload.',
                    'type': 'file'
                },
                {
                    'name': 'resource_path_ips',
                    'title': 'Path to IPs XML resource (SMB/URL)',
                    'type': 'string'
                },
                {
                    'name': 'file_path_subnets',
                    'title': 'Upload subnets XML file',
                    'description': 'Select a file to upload.',
                    'type': 'file'
                },
                {
                    'name': 'resource_path_subnets',
                    'title': 'Path to subnets XML resource (SMB/URL)',
                    'type': 'string'
                },
                {
                    'name': 'file_path_interfaces',
                    'title': 'Upload interfaces XML file',
                    'description': 'Select a file to upload.',
                    'type': 'file'
                },
                {
                    'name': 'resource_path_interfaces',
                    'title': 'Path to interfaces XML resource (SMB/URL)',
                    'type': 'string'
                },
            ],
            'required': [
                *remote_file_consts.FILE_SCHEMA_REQUIRED
            ],
            'type': 'array'
        }

    @staticmethod
    def _is_valid_mac(mac_str: str) -> bool:
        try:
            netaddr.EUI(mac_str)
            return True
        except Exception as e:
            logger.debug(f'{mac_str} is not a valid MAC address: {str(e)}')
        return False

    # pylint: disable=too-many-statements,too-many-branches
    @classmethod
    def _parse_ifaces_info(cls, device, device_raw):
        all_ifaces_raw = device_raw.pop('x_ifaces', [])
        if not isinstance(all_ifaces_raw, list):
            logger.debug(f'Invalid interfaces list: {all_ifaces_raw}')
            return
        for iface_raw in all_ifaces_raw:
            if not isinstance(iface_raw, dict):
                logger.debug(f'Invalid iface dict: {iface_raw}')
                continue
            phys_addr = iface_raw.get('physicalAddress')
            mac_addr = phys_addr if cls._is_valid_mac(phys_addr) else None
            iface_ips, iface_subnets = cls._extract_ips_and_subnets(iface_raw)
            if iface_ips:
                # Add the NIC to the device itself
                try:
                    device.add_nic(
                        mac_addr,
                        iface_ips,
                        iface_subnets or None,
                        name=iface_raw.get('ifName') or None,
                        speed=iface_raw.get('speed') or None)
                except Exception as e:
                    logger.warning(f'Failed to add NIC: {str(e)}')

            # Now try to add the iface to adapter specific data
            try:
                iface_obj = NNMIInterface(  # Build the basic object, then parse more specific data onto it
                    iface_id=iface_raw.get('id'),
                    uuid=iface_raw.get('uuid'),
                    name=iface_raw.get('ifName'),
                    iface_type=int_or_none(iface_raw.get('ifType')),
                    iface_index=int_or_none(iface_raw.get('ifIndex')),
                    description=iface_raw.get('ifDescr'),
                    physical_addr=phys_addr,
                    cdp=iface_raw.get('cdp'),
                    speed=iface_raw.get('speed'),
                    created=parse_date(iface_raw.get('ifcreatetime') or iface_raw.get('ifCreateTime')),
                    modified=parse_date(iface_raw.get('ifmodtime') or iface_raw.get('ifModTime')),
                    status=iface_raw.get('status'),
                    mgmt_mode=iface_raw.get('managementMode'),
                    mgmt_state=iface_raw.get('managementState')
                )
                # Capabilities
                try:
                    capabilities = iface_raw.get('capabilities')
                    if isinstance(capabilities, dict):
                        cap_list = capabilities.get('capability')
                        if cap_list and isinstance(cap_list, list):
                            iface_obj.capabilities = cap_list
                except Exception as e:
                    logger.debug(f'Failed to set iface capabilities for {phys_addr}: {str(e)}')
                # Extended attributes
                try:
                    ext_attrs = cls._parse_extended_attributes(iface_raw.get('extendedAttributes'))
                    if ext_attrs:
                        iface_obj.ext_attrs = ext_attrs
                except Exception as e:
                    logger.debug(f'Failed to parse iface extended attributes for {phys_addr}: {str(e)}')
                # IPs and ips_raw
                try:
                    iface_obj.ips = iface_ips
                    iface_obj.ips_raw = iface_ips
                except Exception as e:
                    logger.warning(f'Failed to add iface IPs for {phys_addr}: {str(e)}')
                # Finally append the iface obj to the device
                device.ifaces.append(iface_obj)
            except Exception as e:
                logger.warning(f'Failed to parse iface info for {iface_raw}: {str(e)}', exc_info=True)
        # Readability: end for iface_raw in...

    @staticmethod
    def _extract_ips_and_subnets(ip_entries):
        ips_raw = list()
        subnets_raw = list()
        # extract IPs and subnets for this interface
        ip_entries = ip_entries.get('x_ips')
        if ip_entries and isinstance(ip_entries, list):
            for ip_entry in ip_entries:
                if not isinstance(ip_entry, dict):
                    continue
                ip_addr = ip_entry.get('value')
                if not is_valid_ip(ip_addr):
                    logger.debug(f'Invalid IP address {ip_addr}')
                    continue
                ips_raw.append(ip_addr)
                # Check and append the subnet (using data injected from subnets XML file)
                x_subnet = ip_entry.get('x_subnet')
                if x_subnet and isinstance(x_subnet, dict):
                    prefix = x_subnet.get('prefix')
                    prefix_length = x_subnet.get('prefixLength')
                    if prefix and prefix_length:
                        subnets_raw.append(f'{prefix}/{prefix_length}')
                    elif x_subnet.get('name'):
                        subnets_raw.append(x_subnet.get('name'))
        return ips_raw, subnets_raw

    @classmethod
    def _parse_orphan_ips(cls, device, device_raw: dict):
        try:
            orphan_ips, orphan_subnets = cls._extract_ips_and_subnets(device_raw)
            if orphan_ips and isinstance(orphan_ips, list):
                device.add_ips_and_macs(ips=orphan_ips)
        except Exception as e:
            logger.warning(f'Failed to parse orphan IPs: {str(e)}')

    @classmethod
    def _fill_nnmi_xml_device_fields(cls, device, device_raw: dict):
        device_id = device.get_field_safe('id')

        device.status = device_raw.get('status')
        device.management_mode = device_raw.get('managementMode')
        device.system_contact = device_raw.get('contact')
        device.location = device_raw.get('location')
        device.snmp_name = device_raw.get('nodesnmpsysname')

        snmp_addr_raw = device_raw.get('nodesnmpaddress')
        if snmp_addr_raw and isinstance(snmp_addr_raw, str):
            try:
                device.snmp_addr = snmp_addr_raw
                device.snmp_addr_raw = [snmp_addr_raw]
            except Exception as e:
                logger.warning(f'Failed to parse snmp address for {device_id}: {str(e)}')

        device.system_object_id = device_raw.get('systemObjectId')
        device.notes = device_raw.get('notes')

        device.created = parse_date(device_raw.get('nodecreatetime'))
        device.modified = parse_date(device_raw.get('nodemodifiedtime'))
        device.status_change = parse_date(device_raw.get('nodelaststatuschange'))

        device.proto_ver = device_raw.get('protocolversion')
        device.discovery_state = device_raw.get('discoveryState')
        device.device_description = device_raw.get('deviceDescription')

        try:
            capabilities = device_raw.get('capabilities')
            if isinstance(capabilities, dict):
                cap_list = capabilities.get('capability')
                if cap_list and isinstance(cap_list, list):
                    device.capabilities = cap_list
        except Exception as e:
            logger.debug(f'Failed to set device capabilities for {device_id}: {str(e)}')

        device.pwr_state = device_raw.get('powerState')
        device.last_state_change = parse_date(device_raw.get('lastStateChange'))

        # parse extended attributes
        ext_attrs_raw = device_raw.get('extendedAttributes')
        try:
            ext_attrs = cls._parse_extended_attributes(ext_attrs_raw)
            if ext_attrs:
                device.ext_attrs = ext_attrs
        except Exception as e:  # Customer specifically asked for the extended attributes so log a warning if fail
            logger.warning(f'Failed to parse extended attributes for device {device_id}: {str(e)}')
            logger.debug(f'Failed to parse extended attributes for {device_raw}', exc_info=True)

    # pylint:disable=too-many-statements, too-many-branches
    def _create_device(self, device_raw):
        device = self._new_device_adapter()
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('name') or '')
            # generic Axonius stuff
            device.first_seen = parse_date(device_raw.get('nodecreatetime'))
            device.last_seen = parse_date(device_raw.get('nodemodifiedtime'))

            device.device_model = device_raw.get('deviceModel')
            device.device_model_family = device_raw.get('deviceFamily')
            device.device_manufacturer = device_raw.get('deviceVendor')
            device.uuid = device_raw.get('uuid')
            device.description = device_raw.get('deviceDescription')
            device.hostname = device_raw.get('name')
            device.name = device_raw.get('shortname')
            device.device_managed_by = device_raw.get('contact')
            device.description = device_raw.get('deviceDescription')  # an actual short description most of the time

            try:
                device.figure_os(device_raw.get('description'))  # This is usually an OS description based on samples
            except Exception as e:
                logger.warning(f'Failed to parse device OS for {device.id}: {str(e)}')

            # Parse network information - generic NIC and adapter-specific NIC info
            try:
                self._parse_ifaces_info(device, device_raw)
                self._parse_orphan_ips(device, device_raw)
            except Exception as e:
                logger.warning(f'Failed to parse interfaces, ips, and subnets for {device.id}: {str(e)}')

            # try to parse SNMP IP as extra ips
            snmp_ip = device_raw.get('nodesnmpaddress')
            if snmp_ip:
                try:
                    device.add_ips_and_macs(ips=[snmp_ip])
                except Exception:
                    logger.exception(f'Failed to set IP from {snmp_ip} for {device.id}')

            # Fill specific fields
            self._fill_nnmi_xml_device_fields(device, device_raw)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching HpNnmi Device for {device_raw}')
            return None

    @staticmethod
    def _parse_extended_attributes(ext_attrs_raw):
        ext_attrs = list()
        if isinstance(ext_attrs_raw, dict):
            attrs_raw = ext_attrs_raw.get('attribute') or []
            if isinstance(attrs_raw, dict):
                attrs_raw = [attrs_raw]
            if attrs_raw and isinstance(attrs_raw, list):
                for attr_raw_dict in attrs_raw:
                    if not isinstance(attr_raw_dict, dict):
                        logger.warning(f'Unable to parse extended attribute: expected dict, '
                                       f'got {attr_raw_dict} instead.')
                        continue
                    attr_name = attr_raw_dict.get('name')
                    attr_val = attr_raw_dict.get('value')
                    try:
                        ext_attrs.append(ExtendedAttribute(name=attr_name, val=attr_val))
                    except Exception:
                        logger.warning(f'Failed to parse extended attribute from {attr_name}: {attr_val}')
            else:
                logger.warning(f'Failed to parse extended attributes from {attrs_raw}')
        return ext_attrs

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
