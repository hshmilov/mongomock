import logging
import datetime

from axonius.devices.device_adapter import (DeviceAdapter,
                                            DeviceAdapterNetworkInterface,
                                            DeviceAdapterVlan,
                                            DeviceAdapterNeighbor,
                                            AdapterProperty)
from axonius.fields import Field
from axonius.blacklists import JUNIPER_NON_UNIQUE_MACS

logger = logging.getLogger(f'axonius.{__name__}')


class JuniperDeviceAdapter(DeviceAdapter):
    device_type = Field(str, 'Device Type', enum=['LLDP Device', 'ARP Device',
                                                  'FDB Device', 'Juniper Device', 'Juniper Space Device'])
    connection_status = Field(str, 'Connection Status', enum=['up', 'down'])


def _get_lldp_id(lldp_raw_device):
    """ The id field is a little bit messy becuse we want the device id
        to refer to all the different mac addresses """
    macs = []

    for _, entry in lldp_raw_device:
        if entry.get('lldp-remote-chassis-id-subtype') == 'Mac address':
            macs.append(entry.get('lldp-remote-chassis-id'))

    # filter empty and None macs
    macs = sorted(list(filter(bool, macs)))
    if not macs:
        raise ValueError('Unable to create id for device')

    first_mac = macs[0]
    return '_'.join(['JUNIPER_LLDP', first_mac])


def create_lldp_device(create_device_func, raw_device):
    for device_name, lldp_raw_device in raw_device.items():
        try:
            # Handle empty device name
            if isinstance(device_name, int):
                device_name = ''

            id_ = _get_lldp_id(lldp_raw_device)
            device = create_device_func()
            device.id = id_
            device.device_type = 'LLDP Device'
            device.adapter_properties = [AdapterProperty.Network.name]
            all_macs = []
            for connected_device_name, entry in lldp_raw_device:
                mac = ''
                iface_name = ''

                chassis_subtype = entry.get('lldp-remote-chassis-id-subtype')
                port_subtype = entry.get('lldp-remote-port-id-subtype')
                if chassis_subtype == 'Mac address':
                    mac = entry.get('lldp-remote-chassis-id', '')
                else:
                    logger.warning(f'unknown id-subtype {chassis_subtype}')

                if port_subtype == 'Interface name':
                    iface_name = entry.get('lldp-remote-port-id', '')
                else:
                    logger.warning(f'unknown port-subtype {port_subtype}')

                # The following field changed in juniper models, try to fetch both
                connected_iface_name = entry.get(
                    'lldp-local-port-id', '') or entry.get('lldp-local-interface', '')

                device.name = device_name

                if mac not in all_macs:
                    # New mac - add new nic
                    try:
                        device.add_nic(name=iface_name, mac=mac)
                    except Exception:
                        logger.error('Failed to add nic for device')
                    all_macs.append(mac)

                # Add connection TODO: This connection should be bi-directonal -> we want the data
                # to bee seen both from local device, and remote device in the gui
                connected_device = DeviceAdapterNeighbor()
                connected_device.remote_name = connected_device_name
                connected_device.connection_type = 'Direct'
                if iface_name:
                    connected_device.local_ifaces.append(DeviceAdapterNetworkInterface(name=iface_name))
                connected_device.remote_ifaces.append(DeviceAdapterNetworkInterface(name=connected_iface_name))

                device.connected_devices.append(connected_device)
            device.set_raw(dict(lldp_raw_device))
            yield device
        except Exception:
            logger.exception(
                f'Problem with parsing lldp device {lldp_raw_device}')


def create_arp_device(create_device_func, raw_device):

    for arp_raw_device in raw_device.values():
        try:

            if arp_raw_device['mac_address'].lower() in ['*', 'unspecified']:
                logger.debug(f'Ignoring mac {arp_raw_device["mac_address"]}')
                continue

            if arp_raw_device['mac_address'].upper() in JUNIPER_NON_UNIQUE_MACS:
                logger.debug('Non unique mac {arp_raw_device["mac_address"]}')
                continue

            device = create_device_func()
            first_name = sorted(list(arp_raw_device['linked_devices'].keys()))[0]
            device.id = '_'.join(['JUINPER_ARP', arp_raw_device['mac_address'], first_name])
            device.add_nic(arp_raw_device['mac_address'])
            device.device_type = 'ARP Device'
            device.adapter_properties = [AdapterProperty.Network.name]
            try:
                device.set_related_ips(list(arp_raw_device['related_ips']))
            except Exception:
                logger.exception(f'Problem getting IPs in {arp_raw_device}')

            for name, ifaces in arp_raw_device['linked_devices'].items():
                try:
                    neighbor_device = DeviceAdapterNeighbor()
                    neighbor_device.remote_name = name
                    neighbor_device.connection_type = 'Indirect'
                    for iface in ifaces:
                        interface = DeviceAdapterNetworkInterface()
                        interface.name = iface
                        neighbor_device.remote_ifaces.append(interface)
                    device.connected_devices.append(neighbor_device)
                except Exception:
                    logger.exception(f'Problem adding connected device {arp_raw_device}')

            try:
                device.set_raw({'mac': arp_raw_device['mac_address'],
                                'names': list(arp_raw_device['names']),
                                'connected_devices': list(arp_raw_device['linked_devices']),
                                'ips': list(arp_raw_device['related_ips']),
                                })
            except Exception:
                logger.exception(f'Problem setting raw in {arp_raw_device}')
                device.set_raw({})
            yield device
        except Exception:
            logger.exception(
                f'Problem with pasrsing arp device {arp_raw_device}')


# pylint: disable=R1702
# pylint: disable=R0912


def _create_fdb_device(create_device_func, mac, fdb_raw_device):
    if mac.lower() in ['*', 'unspecified']:
        logger.debug(f'Ignoring mac {mac}')
        return None

    if mac.upper() in JUNIPER_NON_UNIQUE_MACS:
        logger.debug(f'Non unique mac {mac}')
        return None

    device = create_device_func()
    first_name = sorted(list(fdb_raw_device.keys()))[0]
    device.id = '_'.join(['JUINPER_FDB', mac, first_name])
    device.add_nic(mac)
    device.device_type = 'FDB Device'
    device.adapter_properties = [AdapterProperty.Network.name]

    for connected_device_name, connected_device_data in fdb_raw_device.items():
        try:
            connected_device = DeviceAdapterNeighbor()
            connected_device.remote_name = connected_device_name
            connected_device.connection_type = 'Indirect'
            for iface, entries in connected_device_data.items():
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
                    vlan_id = entry.get('vlanid', '')

                    if not vlan_name and not vlan_id:
                        logger.warning('empty vlan continue')
                        continue

                    new_vlan = DeviceAdapterVlan()
                    new_vlan.name = vlan_name
                    try:
                        if vlan_id:
                            new_vlan.tagid = int(vlan_id)
                    except ValueError:
                        logger.error(f'Invalid vlan_id {vlan_id}')

                    interface.vlan_list.append(new_vlan)

                if not interface.vlan_list:
                    # We didn't get any Learn entires - ignore iface
                    logger.debug('Ignoring empty iface')
                    continue

                connected_device.remote_ifaces.append(interface)

            if not connected_device.remote_ifaces:
                # we didn't get any linked device - dont add device
                logger.debug('Ignore empty device')
                return None
            device.connected_devices.append(connected_device)

        except Exception:
            logger.exception(f'Problem adding linked device {connected_device_data}')

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
    list_, rr = raw_device.get('interface list', ([], None))
    if list_:
        mac = list_[0].get('current-physical-address', '')
    if mac:
        return mac
    return ''


def _get_vlans_for_iface(raw_device, iface_name):
    if not all([field in raw_device for field in ['interface list', 'vlans']]):
        logger.debug('Missing required field')
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

    for index, base_mac in enumerate(raw_device.get('base-mac', [])):
        try:
            device.add_nic(name=f'base-mac{index}', mac=base_mac)
        except Exception:
            logger.exception('Unable to add basic-mac')

    raw, rr = raw_device['interface list']
    for interface in raw:
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
                    vlan_id = raw_vlan.get('interface-vlan-member-tagid', '')
                    try:
                        if vlan_id:
                            new_vlan.tagid = int(vlan_id)
                    except ValueError:
                        logger.error(f'Invalid vlan_id {vlan_id}')

                    vlan_list.append(new_vlan)

            admin_status = interface.get('admin-status')
            operational_status = interface.get('oper-status')
            mac = interface.get('current-physical-address')

            # Ignore weird macs
            if mac.lower() in ['unspecified', '*']:
                mac = None

            name = interface.get('name')
            speed = interface.get('speed')
            mtu = interface.get('mtu')

            # For now set mtu to zero on unlimited
            if mtu.lower() == 'unlimited':
                mtu = 0

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
        device.adapter_properties = [AdapterProperty.Network.name, AdapterProperty.Manager.name]
        device.figure_os('junos')

        # we are running on the endpoint, so the last seen is right now
        device.last_seen = datetime.datetime.now()

        id_ = _get_id_for_juniper(raw_device)
        if not id_:
            raise ValueError('Unable to generate id_')

        device.id = 'JUNIPER_' + id_
        if 'version' in raw_device:
            device.hostname = raw_device['version'].get('host-name', '')
            device.os.build = raw_device['version'].get('version', '')

        # product model and hardware description should be the same,
        # but sometimes we dont have hardware and sometimes the description is virtual
        # chassis (which means multiple models for now we take hardware whenever we can
        device.device_model = raw_device.get('hardware', {}).get('description') or \
            raw_device.get('version', {}).get('product-model', '')

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


def update_connected(devices):
    devices = list(devices)

    other_devices = [device for device in devices if device.device_type != 'Juniper Device']
    juniper_devices = {device.hostname: device for device in devices
                       if device.device_type == 'Juniper Device' and device.to_dict().get('hostname')}

    for other_device in other_devices:
        try:
            if not other_device.to_dict().get('connected_devices'):
                continue

            for connected_device in other_device.connected_devices:
                if not connected_device.to_dict().get('remote_name'):
                    continue

                if not connected_device.to_dict().get('remote_ifaces'):
                    continue

                remote = juniper_devices.get(connected_device.remote_name)
                if not remote:
                    continue

                if not remote.to_dict().get('network_interfaces'):
                    continue

                for iface in connected_device.remote_ifaces:
                    for remote_iface in remote.network_interfaces:
                        if not remote_iface.to_dict().get('name') or not iface.to_dict().get('name'):
                            continue

                        if not remote_iface.to_dict().get('port_type'):
                            continue

                        if remote_iface.name == iface.name and remote_iface.port_type:
                            iface.port_type = remote_iface.port_type
                            if iface.port_type == 'Access':
                                connected_device.connection_type = 'Direct'
        except Exception:
            logger.exception('Failed to update connected')

    return devices


CREATE_DEVICE_CALLBACKS = {
    'ARP Device': create_arp_device,
    'FDB Device': create_fdb_device,
    'LLDP Device': create_lldp_device,
    'Juniper Device': create_juniper_device,
}
