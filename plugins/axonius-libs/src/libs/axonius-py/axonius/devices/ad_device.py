from axonius.devices.device import Device
from axonius.devices.dns_resolvable import DNSResolvableDevice
from axonius.fields import ListField


class ADDevice(Device, DNSResolvableDevice):
    ad_organizational_unit = ListField(str, "Organizational Unit")

    def add_organizational_units(self, distinguished_name):
        for ou in [ou[3:] for ou in distinguished_name.split(",") if ou.startswith("OU=")]:
            self.ad_organizational_unit.append(ou)
