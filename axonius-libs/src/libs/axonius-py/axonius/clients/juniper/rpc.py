""" xml rpc parser for juniper """

import logging

from xml.etree import ElementTree
from collections import defaultdict

logger = logging.getLogger(f"axonius.{__name__}")


def cast_to_xml_if_needed(xml):
    ''' cast argument to xml if it is string
        if we got lxml element, convert to xml'''
    if isinstance(xml, (str, bytes)):
        xml = ElementTree.fromstring(xml)
    return xml


def strip_rpc_if_needed(xml):
    '''
        sometimes juniper xml returns with rpc-reply header, sometimes not.
        strip the header if needed.
    '''
    if gettag(xml.tag) == 'rpc-reply':
        xml = xml[0]
    return xml


def prepare(xml):
    ''' call all pre parsing functions '''
    xml = cast_to_xml_if_needed(xml)
    xml = strip_rpc_if_needed(xml)
    return xml


def gettext(text: str):
    ''' for some reason, somtimes we get string from xml with \n in start and end.
        strip t  - We should investiage more '''

    if text[0] == '\n' and text[-1] == '\n':
        text = text[1:-1]

    return text


def gettag(tag: str):
    ''' sometimes junos tag return with {<version>} prefix, 
        remote it if possible '''

    if tag[0] == '{' and '}' in tag:
        tag = tag[tag.index('}') + 1:]

    return tag


def parse_arps(xmls: list):
    ''' given list of juniper_device_name, return values from 'get-arp-table-information'
        parse it and return raw_device
    '''

    raw_arp_devices = {}
    for juniper_device_name, xml in xmls:
        try:
            xml = prepare(xml)

            if 'arp-table-information' not in gettag(xml.tag):
                logger.warning(
                    'arp-table-information not found, got {0}'.format(gettag(xml.tag)))
                continue

            for item in xml:
                try:
                    if 'arp-table-entry' not in gettag(item.tag):
                        logger.warning(
                            'arp-table-entry not found, got {0}'.format(gettag(item.tag)))
                        continue

                    mac_address = None
                    ip_address = None
                    name = None
                    interface = None
                    for xml_arp_property in item:
                        if 'mac-address' in gettag(xml_arp_property.tag):
                            mac_address = gettext(xml_arp_property.text)
                        if 'ip-address' in gettag(xml_arp_property.tag):
                            ip_address = gettext(xml_arp_property.text)
                        if 'hostname' in gettag(xml_arp_property.tag):
                            name = gettext(xml_arp_property.text)
                        if 'interface-name' in gettag(xml_arp_property.tag):
                            interface = gettext(xml_arp_property.text)
                    if mac_address is None:
                        continue
                    if mac_address not in raw_arp_devices:
                        raw_arp_devices[mac_address] = defaultdict(set)

                    if "linked_devices" not in raw_arp_devices[mac_address]:
                        raw_arp_devices[mac_address]["linked_devices"] = defaultdict(set)

                    if juniper_device_name not in raw_arp_devices[mac_address]["linked_devices"]:
                        raw_arp_devices[mac_address]["linked_devices"][juniper_device_name] = set()

                    raw_arp_devices[mac_address]['mac_address'] = mac_address
                    if ip_address is not None:
                        raw_arp_devices[mac_address]['related_ips'].add(ip_address)
                    if interface is not None:
                        raw_arp_devices[mac_address]["linked_devices"][juniper_device_name].add(interface)
                    if name is not None:
                        raw_arp_devices[mac_address]['name'].add(name)
                except Exception:
                    logger.exception(f'Failed to parse item {item}')
                    continue
        except Exception:
            logger.exception(f'Failed to parse xml {xml}')
            continue

    return raw_arp_devices


def parse_fdbs(xmls):
    ''' parse list of juniper_device_name, xml from 'get-ethernet-switching-table-information' '''

    results = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for juniper_device_name, xml in xmls:
        try:
            xml = prepare(xml)

            if gettag(xml.tag) == 'l2ng-l2ald-rtb-macdb':
                ret = parse_l2ng(xml)
            elif gettag(xml.tag) == 'ethernet-switching-table-information':
                ret = parse_ethernet_switching(xml)
            else:
                logger.error('got invalid tag {0}'.format(gettag(xml.tag)))
                continue

            # now reorder the data
            for entry in ret:
                if 'iface' not in entry:
                    logger.error(f'missing iface for entry {entry}')
                    continue

                for iface in entry['iface']:
                    results[entry['mac-address']][juniper_device_name][iface].append(entry)
        except Exception:
            logger.warning(f'Failed to parse xml {xml}')
            continue

    return results


def parse_l2ng(xml):
    ''' parse l2ng xml, unfortunately some of the fields change between version,
        so we must be very carefull when we parse '''
    entries = []

    for vlan in xml:
        if gettag(vlan.tag) != 'l2ng-l2ald-mac-entry-vlan':
            logger.warning(
                'l2ng-l2ald-mac-entry-vlan not found, got {0}'.format(gettag(vlan.tag)))
            continue

        vlanid = None
        for entry in vlan:
            new_entry = {}
            new_entry['iface'] = []
            if gettag(entry.tag) == 'l2ng-l2-vlan-id':
                vlanid = gettext(entry.text)
                continue

            if gettag(entry.tag) != 'l2ng-mac-entry':
                logger.warning(
                    'l2ng-mac-entry not found, got {0}'.format(gettag(entry.tag)))
                continue

            for field in entry:
                if gettag(field.tag) == 'l2ng-l2-mac-address':
                    new_entry['mac-address'] = gettext(field.text)

                if gettag(field.tag) == 'l2ng-l2-mac-vlan-name':
                    new_entry['vlan-name'] = gettext(field.text)

                if gettag(field.tag) == 'l2ng-l2-mac-flags':
                    new_entry['flags'] = gettext(field.text)

                if gettag(field.tag) == 'l2ng-l2-mac-logical-interface':
                    new_entry['iface'].append(gettext(field.text))

                new_entry['vlanid'] = vlanid

            if 'mac-address' not in new_entry:
                logger.error(f'Got empty mac entry {new_entry}, skipping')
                continue

            entries.append(new_entry)
    return entries


def parse_ethernet_switching(xml):
    ''' parse single route xml from  'get-ethernet-switching-table-information' '''

    entries = []
    for vlan in xml:
        if gettag(vlan.tag) != 'ethernet-switching-table':
            logger.warning(
                'ethernet-switching-table not found, got {0}'.format(gettag(vlan.tag)))
            continue

        for entry in vlan:
            new_entry = {}

            if gettag(entry.tag) != 'mac-table-entry':
                logger.warning(
                    'l2ng-mac-entry not found, got {0}'.format(gettag(entry.tag)))
                continue

            for field in entry:
                if gettag(field.tag) == 'mac-address':
                    new_entry['mac-address'] = gettext(field.text)

                if gettag(field.tag) == 'mac-vlan':
                    new_entry['vlan-name'] = gettext(field.text)

                if gettag(field.tag) == 'mac-type':
                    new_entry['flags'] = gettext(field.text)

                if gettag(field.tag) == 'mac-interfaces-list':
                    new_entry['iface'] = []
                    for iface in field:
                        if gettag(iface.tag) != 'mac-interfaces':
                            logger.error(f'Invalid tag {gettag(iface.tag)}')
                            continue
                        new_entry['iface'].append(gettext(iface.text))

            if 'mac-address' not in new_entry:
                logger.error(f'Got empty mac entry {new_entry}, skipping')
                continue

            entries.append(new_entry)
    return entries


def parse_device(type_, raw_datas):
    if type_ not in PARSE_DEVICE_CALLBACKS:
        raise ValueError(f'Unknown type {type_}')

    return PARSE_DEVICE_CALLBACKS[type_](raw_datas)


PARSE_DEVICE_CALLBACKS = {
    'ARP Device': parse_arps,
    'FDB Device': parse_fdbs,
}
