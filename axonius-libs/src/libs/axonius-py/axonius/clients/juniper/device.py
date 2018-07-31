import logging

from axonius.devices.device_adapter import (DeviceAdapter,
                                            DeviceAdapterNetworkInterface,
                                            DeviceAdapterVlan, SmartJsonClass)
from axonius.fields import Field, ListField

logger = logging.getLogger(f'axonius.{__name__}')


class LinkedDevicesAdapter(SmartJsonClass):
    device_name = Field(str, 'Device Name')
    interfaces = ListField(DeviceAdapterNetworkInterface, 'interfaces')


class JuniperDeviceAdapter(DeviceAdapter):
    device_type = Field(str, 'Device Type', enum=['ARP Device', 'FDB Device', 'Juniper Device'])
    linked_devices = ListField(LinkedDevicesAdapter, 'Linked Devices')


def create_arp_device(create_device_func, raw_device):

    for arp_raw_device in raw_device.values():
        try:
            device = create_device_func()
            names = '_'.join(sorted(list(arp_raw_device['linked_devices'].keys())))
            device.id = '_'.join(['JUINPER_ARP', arp_raw_device['mac_address'], names])
            device.add_nic(arp_raw_device['mac_address'])
            device.device_type = 'ARP Device'
            try:
                device.set_related_ips(list(arp_raw_device['related_ips']))
            except Exception:
                logger.exception(f'Problem getting IPs in {arp_raw_device}')

            for name, ifaces in arp_raw_device['linked_devices'].items():
                try:
                    linked_device = LinkedDevicesAdapter()
                    linked_device.device_name = name
                    for iface in ifaces:
                        interface = DeviceAdapterNetworkInterface()
                        interface.name = iface
                        linked_device.interfaces.append(interface)
                    device.linked_devices.append(linked_device)
                except Exception:
                    logger.exception(f'Problem adding linked device {arp_raw_device}')

            try:
                device.set_raw({'mac': arp_raw_device['mac_address'],
                                'names': list(arp_raw_device['names']),
                                'linked_devices': list(arp_raw_device['linked_devices']),
                                'ips': list(arp_raw_device['related_ips']),
                                })
            except Exception:
                logger.exception(f'Problem setting raw in {arp_raw_device}')
                device.set_raw({})
            yield device
        except Exception:
            logger.exception(
                f'Problem with pasrsing arp device {arp_raw_device}')


def _create_fdb_device(create_device_func, mac, fdb_raw_device):
    if mac == '*':
        logger.debug('Ignoring mac *')
        return None

    device = create_device_func()
    names = '_'.join(sorted(list(fdb_raw_device.keys())))
    device.id = '_'.join(['JUINPER_FDB', mac, names])
    device.add_nic(mac)
    device.device_type = 'FDB Device'

    for linked_device_name, linked_device_data in fdb_raw_device.items():
        try:
            linked_device = LinkedDevicesAdapter()
            linked_device.device_name = linked_device_name
            for iface, entries in linked_device_data.items():
                if iface == 'All-members':
                    logger.debug('Igonring All-members entry')
                    continue

                interface = DeviceAdapterNetworkInterface()
                interface.name = iface
                for entry in entries:
                    # For now we only parse dynamic entries
                    if entry.get('flags') not in ['D', 'Learn']:
                        logger.debug(f'ignoring {entry}')
                        continue
                    vlan_name = entry.get('vlan-name', '')
                    vlanid = entry.get('vlanid', '')
                    if vlanid != '':
                        vlan_name = f'{vlan_name} ({vlanid})'
                    interface.vlan_list.append(vlan_name)

                if not interface.vlans:
                    # We didn't get any Learn entires - ignore iface
                    logger.debug('Ignoring empty iface')
                    continue

                linked_device.interfaces.append(interface)

            if not linked_device.interfaces:
                # we didn't get any linked device - dont add device
                logger.debug('Ignore empty device')
                return None
            device.linked_devices.append(linked_device)

        except Exception:
            logger.exception(f'Problem adding linked device {linked_device_data}')

    try:
        device.set_raw({'mac': mac,
                        'fdb': fdb_raw_device,
                        })
    except Exception:
        logger.exception(f'Problem setting raw in {fdb_raw_device}')
        device.set_raw({})
    return device


def create_fdb_device(create_device_func, raw_device):
    """ create the fdb device, for now we only reference dynamic entries """
    for mac, fdb_raw_device in raw_device.items():
        try:
            dev = _create_fdb_device(create_device_func, mac, fdb_raw_device)
            if dev:
                yield dev
        except Exception:
            logger.exception(f'Failed to create raw device for {fdb_raw_device}')
            continue


def _get_id_for_juniper(raw_device):
    """ if we have serial use serial for id, else use first interface, else fail """
    serial = raw_device.get('hardware', {}).get('serial-number', '')
    if serial:
        return serial
    list_ = raw_device.get('interface list', [])
    if list_:
        mac = list_[0].get('current-physical-address', '')
    if mac:
        return mac
    return ''


def _get_vlans_for_iface(raw_device, iface_name):
    if not all([field in raw_device for field in ['interface list', 'vlans']]):
        logger.error('Missing required field')
        return None

    vlans = list(filter(lambda vlan: vlan.get('interface-name') == iface_name, raw_device['vlans']))
    if len(vlans) != 1:
        logger.debug(f'unable to match vlan for iface {iface_name}')
        return None

    return vlans[0]


def _juniper_add_nic(device, raw_device):
    """ add nic for given juniper device """
    if 'interface list' not in raw_device:
        return

    for interface in raw_device['interface list']:
        try:
            vlan_list = []
            raw_vlan = _get_vlans_for_iface(raw_device, interface.get('name', ''))
            port_type = None
            if raw_vlan:
                port_type = raw_vlan.get('interface-port-mode')
                for raw_vlan in raw_vlan.get('vlans', []):
                    new_vlan = DeviceAdapterVlan()
                    new_vlan.name = raw_vlan.get('interface-vlan-name', '')
                    new_vlan.tagness = raw_vlan.get('interface-vlan-member-tagness', '')
                    new_vlan.tagid = raw_vlan.get('interface-vlan-member-tagid', '')
                    vlan_list.append(new_vlan)

            admin_status = interface.get('admin-status')
            operational_status = interface.get('oper-status')
            mac = interface.get('current-physical-address')
            name = interface.get('name')
            speed = interface.get('speed')
            mtu = interface.get('mtu')
            ips = interface.get('ips')
            subnets = interface.get('subnets')

            device.add_nic(mac=mac, ips=ips, subnets=subnets, name=name,
                           speed=speed, mtu=mtu, operational_status=operational_status, admin_status=admin_status,
                           vlans=vlan_list, port_type=port_type)
        except Exception:
            logging.exception(f'Unable to add interface {interface}')


def create_juniper_device(create_device_func, raw_device):
    """ create juniper device by basic info rpc dict """
    try:
        device = create_device_func()
        device.device_type = 'Juniper Device'
        device.figure_os('junos')

        id_ = _get_id_for_juniper(raw_device)
        if not id_:
            raise ValueError('Unable to generate id_')

        device.id = 'JUNIPER_' + id_
        if 'version' in raw_device:
            device.hostname = raw_device['version'].get('hostname', '')
            device.os.build = raw_device['version'].get('version', '')

            # product model and description should be the same, but sometimes we dont have hardware
            device.device_model = raw_device.get('hardware', {}).get('description', '') \
                or raw_device['version'].get('product-model', '')

        device.device_serial = raw_device.get('hardware', {}).get('serial-number', '')
        _juniper_add_nic(device, raw_device)
        device.set_raw(raw_device)
        yield device
    except Exception:
        logger.exception(f'Failed to create device {raw_device}')


def create_device(create_device_func, type_, raw_device):
    if type_ not in CREATE_DEVICE_CALLBACKS:
        raise ValueError(f'Unknown type {type_}')

    yield from CREATE_DEVICE_CALLBACKS[type_](create_device_func, raw_device)


CREATE_DEVICE_CALLBACKS = {
    'ARP Device': create_arp_device,
    'FDB Device': create_fdb_device,
    'Juniper Device': create_juniper_device,
}
