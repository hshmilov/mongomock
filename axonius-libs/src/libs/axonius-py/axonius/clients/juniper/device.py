import logging

from axonius.devices.device_adapter import DeviceAdapter, DeviceAdapterNetworkInterface, SmartJsonClass
from axonius.fields import Field, ListField

logger = logging.getLogger(f"axonius.{__name__}")


class LinkedDevicesAdapter(SmartJsonClass):
    device_name = Field(str, "Device Name")
    interfaces = ListField(DeviceAdapterNetworkInterface, "interfaces")


class JuniperDeviceAdapter(DeviceAdapter):
    device_type = Field(str, 'Device Type', enum=['ARP Device', 'FDB Device', 'Juniper Device'])
    linked_devices = ListField(LinkedDevicesAdapter, "Linked Devices")


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
                logger.exception(f"Problem getting IPs in {arp_raw_device}")

            for name, ifaces in arp_raw_device["linked_devices"].items():
                try:
                    linked_device = LinkedDevicesAdapter()
                    linked_device.device_name = name
                    for iface in ifaces:
                        interface = DeviceAdapterNetworkInterface()
                        interface.name = iface
                        linked_device.interfaces.append(interface)
                    device.linked_devices.append(linked_device)
                except Exception:
                    logger.exception(f"Problem adding linked device {arp_raw_device}")

            try:
                device.set_raw({'mac': arp_raw_device['mac_address'],
                                'names': list(arp_raw_device['names']),
                                'linked_devices': list(arp_raw_device["linked_devices"]),
                                'ips': list(arp_raw_device['related_ips']),
                                })
            except Exception:
                logger.exception(f"Problem setting raw in {arp_raw_device}")
                device.set_raw({})
            yield device
        except Exception:
            logger.exception(
                f"Problem with pasrsing arp device {arp_raw_device}")


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
                    if entry.get("flags") not in ["D", "Learn"]:
                        logger.debug(f'ignoring {entry}')
                        continue
                    vlan_name = entry.get("vlan-name", "")
                    vlanid = entry.get("vlanid", "")
                    if vlanid != "":
                        vlan_name = f"{vlan_name} ({vlanid})"
                    interface.vlans.append(vlan_name)

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
            logger.exception(f"Problem adding linked device {linked_device_data}")

    try:
        device.set_raw({'mac': mac,
                        'fdb': fdb_raw_device,
                        })
    except Exception:
        logger.exception(f"Problem setting raw in {fdb_raw_device}")
        device.set_raw({})
    return device


def create_fdb_device(create_device_func, raw_device):
    ''' create the fdb device, for now we only reference dynamic entries '''
    for mac, fdb_raw_device in raw_device.items():
        try:
            dev = _create_fdb_device(create_device_func, mac, fdb_raw_device)
            if dev:
                yield dev
        except Exception:
            logger.exception(f"Failed to create raw device for {fdb_raw_device}")
            continue


def create_device(create_device_func, type_, raw_device):
    if type_ not in CREATE_DEVICE_CALLBACKS:
        raise ValueError(f'Unknown type {type_}')

    yield from CREATE_DEVICE_CALLBACKS[type_](create_device_func, raw_device)


CREATE_DEVICE_CALLBACKS = {
    'ARP Device': create_arp_device,
    'FDB Device': create_fdb_device,
}
