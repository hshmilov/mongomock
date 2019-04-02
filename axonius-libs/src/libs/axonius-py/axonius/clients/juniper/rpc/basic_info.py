""" xml basic info parser for juniper """

import logging
import copy
import re

from typing import List, Tuple

from axonius.clients.juniper.rpc.utils import gettext, gettag, prepare
from axonius.utils.xml2json_parser import Xml2Json

logger = logging.getLogger(f'axonius.{__name__}')


def fix_subnet(text):
    """ sometimes subnet field is removing '0' for the end, add it if it's missing """
    ip, subnet = text.split('/')
    bytes_ = ip.split('.')
    bytes_ += ['0' for _ in range(4 - len(bytes_))]
    ip = '.'.join(bytes_)
    return '/'.join([ip, subnet])


def parse_basic_info(xmls: Tuple[str, List[Tuple[str, str]]]):
    """
        Parse basic info is a little bit diffrenent form all the other parser,
        It takes a list of different xml, parse each one and return basic info device
    """
    raw_data = {}
    device_name, xmls = xmls
    for type_, xml in xmls:
        try:
            if type_ not in BASIC_INFO_TYPES:
                logger.error(f'Invalid type {type_}')
                continue

            xml = prepare(xml)
            parse_callback = BASIC_INFO_TYPES[type_]
            raw_data[type_] = parse_callback(xml)
        except Exception as e:
            logger.exception(f'Exception while handling type {type_}')

    # Monkey patch device_name if we didn't get it yet
    if 'version' not in raw_data:
        raw_data['version'] = {}
    if not raw_data['version'].get('host-name'):
        raw_data['version']['host-name'] = device_name
    return raw_data


def _parse_interface_entry(dict_, tag, text):
    if tag in ['name', 'speed', 'current-physical-address', 'mtu',
               'admin-status', 'oper-status', 'address-family-name']:
        dict_[tag] = text

    if tag == 'ifa-local':
        if 'ips' not in dict_:
            dict_['ips'] = [text]
        else:
            dict_['ips'].append(text)

    if tag == 'ifa-destination':
        text = fix_subnet(text)
        if 'subnets' not in dict_:
            dict_['subnets'] = [text]
        else:
            dict_['subnets'].append(text)


# pylint: disable=R1702
def parse_interface_list(xml):
    """ parse get-interface-information xml """
    result = []
    if gettag(xml.tag) != 'interface-information':
        raise ValueError(f'interface-information not found got {gettag(xml.tag)}')

    for interface_list in xml:
        entry = {}
        for interface in interface_list:
            logical_interfaces = []
            tag = gettag(interface.tag)
            text = gettext(interface.text)

            _parse_interface_entry(entry, tag, text)

            if tag == 'logical-interface':
                # new logical entry, copy entry and add data
                logical_interface = copy.copy(entry)
                for field in interface:
                    tag = gettag(field.tag)
                    text = gettext(field.text)
                    _parse_interface_entry(logical_interface, tag, text)
                    if tag == 'address-family':
                        for address_family_field in field:
                            tag = gettag(address_family_field.tag)
                            text = gettext(address_family_field.text)
                            _parse_interface_entry(logical_interface, tag, text)
                            if tag == 'interface-address':
                                for interface_address_field in address_family_field:
                                    tag = gettag(interface_address_field.tag)
                                    text = gettext(interface_address_field.text)
                                    _parse_interface_entry(logical_interface, tag, text)

                logical_interfaces.append(logical_interface)

        if 'current-physical-address' not in entry:
            logging.debug(f'skipping entry {entry}')
            continue

        result.append(entry)
        for logical_interface in logical_interfaces:
            result.append(logical_interface)

    return result, Xml2Json(xml).result


def parse_hardware(xml):
    """ parse get-chassis-inventory """
    result = {}

    if gettag(xml.tag) != 'chassis-inventory':
        raise ValueError(f'chassis inventory not found got {gettag(xml.tag)}')

    # for now we only parse the "Chasis" entry in order to get the main board name and serial
    for field in xml:
        tag = gettag(field.tag)
        text = gettext(field.text)
        if tag == 'chassis':
            for entry in field:
                tag = gettag(entry.tag)
                text = gettext(entry.text)
                if tag in ['serial-number', 'description']:
                    result[tag] = text
    return result


def parse_version(xml):
    """ parse get-software-information xml """
    if gettag(xml.tag) != 'software-information':
        raise ValueError(f'software-information not found got {gettag(xml.tag)}')

    entry = {}
    for field in xml:
        tag = gettag(field.tag)
        text = gettext(field.text)
        if tag in ['host-name', 'product-model']:
            entry[tag] = text

        if tag == 'package-information':
            version = gettext(field[1].text)
            match = re.match(r'.*\[(.*)\].*', version)
            if match:
                entry['version'] = match.groups()[0]
            break
    return entry


def parse_switching_interface(xml):
    """ parse get-ethernet-switching-interface-information detail version 1"""
    result = []
    if gettag(xml.tag) != 'switching-interface-information':
        raise ValueError(f'switching-interface-information not found got {gettag(xml.tag)}')

    for interface in xml:
        entry = {'vlans': []}
        for interface_field in interface:
            tag = gettag(interface_field.tag)
            text = gettag(interface_field.text)

            if tag in ['interface-name', 'interface-state', 'interface-port-mode']:
                entry[tag] = text

            if tag == 'interface-vlan-member-list':
                for vlan_member in interface_field:
                    vlan = {}
                    for vlan_member_field in vlan_member:
                        tag = gettag(vlan_member_field.tag)
                        text = gettag(vlan_member_field.text)

                        if tag in ['interface-vlan-name', 'interface-vlan-member-tagid',
                                   'interface-vlan-member-tagness']:
                            vlan[tag] = text
                    entry['vlans'].append(vlan)
        result.append(entry)
    return result


def parse_l2ald_interface(xml):
    """ parse get-ethernet-l2ng-l2ald-iff-interface-information detail version 1"""
    fields = {
        'l2iff-interface-name': 'interface-name',
        'l2iff-interface-interface-type': 'type',
        'l2iff-interface-trunk-vlan': 'interface-port-mode',
        'l2iff-interface-vlan-id':    'interface-vlan-member-tagid',
        'l2iff-interface-vlan-name': 'interface-vlan-name',
        'l2iff-interface-vlan-member-tagness': 'interface-vlan-member-tagness',
    }

    result_list = []
    result = {}
    if gettag(xml.tag) != 'l2ng-l2ald-iff-interface-information':
        raise ValueError(f'l2ng-l2ald-iff-interface-information not found got {gettag(xml.tag)}')

    for entry_raw in xml:
        entry = {}
        if gettag(entry_raw.tag) != 'l2ng-l2ald-iff-interface-entry':
            logger.warning(f'l2ng-l2ald-iff-interface-entry not found got {gettag(entry_raw.tag)}')
            continue

        for field in entry_raw:
            if gettag(field.tag) not in fields:
                continue

            entry[fields[gettag(field.tag)]] = gettext(field.text)

        if not entry.get('type', '').startswith('IFBD'):
            continue

        if 'interface-name' not in entry:
            continue

        interface_name = entry['interface-name']
        if interface_name not in result:
            result[interface_name] = {'interface-name': interface_name, 'vlans': []}

        if 'interface-port-mode' in entry:
            if str(entry['interface-port-mode']) == '0' and \
                    not result[interface_name].get('interface-port-mode'):
                result[interface_name]['interface-port-mode'] = 'Trunk'
            del entry['interface-port-mode']

        result[interface_name]['vlans'].append(entry)

    return list(result.values())


def parse_vlans(xml):
    if gettag(xml.tag) == 'switching-interface-information':
        result = parse_switching_interface(xml)
    elif gettag(xml.tag) == 'l2ng-l2ald-iff-interface-information':
        result = parse_l2ald_interface(xml)
    else:
        raise ValueError(f'parse vlans got {gettag(xml.tag)}')
    return result


def parse_base_mac(xml):
    result = []
    if gettag(xml.tag) != 'chassis-mac-information':
        raise ValueError(f'base mac not found got {gettag(xml.tag)}')
    for field in xml:
        if gettag(field.tag) == 'fpc-mac-information':
            for fpc in field:
                if gettag(fpc.tag) == 'mac-address':
                    result.append(gettext(fpc.text))
    return result


BASIC_INFO_TYPES = {
    'interface list': parse_interface_list,  # show interfaces
    'hardware': parse_hardware,              # show chassis hardware
    'version': parse_version,                # show version
    'vlans': parse_vlans,                    # show ethernet-switching interfaces detail
    'base-mac': parse_base_mac,
}
