from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField


class RedHatSatelliteDevice(DeviceAdapter):
    cert_name = Field(str, 'Certificate Name')
    environment_name = Field(str, 'Environment')
    hostgroup_title = Field(str, 'Host Group')
    subnet_name = Field(str, 'Subnet name')
    ptable_name = Field(str, 'Partition Table')
    pxe_loader = Field(str, 'PXE Loader')
    capabilities = ListField(str, 'Capabilities')
    compute_profile = Field(str, 'Compute Profile')
    compute_resource = Field(str, 'Compute Resource')
    medium_name = Field(str, 'Medium')
    image_name = Field(str, 'Image Name')
    image_file = Field(str, 'Image File')
    global_status_label = Field(str, 'Global Status')
    build_status = Field(str, 'Build Status')
    puppet_status = Field(str, 'Puppet Status')
    puppet_proxy_name = Field(str, 'Puppet Proxy')
    puppet_ca_proxy_name = Field(str, 'Puppet CA Proxy')
    openscap_proxy_name = Field(str, 'OpenSCAP Proxy')
    kickstart_repository = Field(str, 'Kickstart Repository')

    # fields from .content_facet_attributes
    lifecycle_environment_name = Field(str, 'Lifecycle Environment')
    content_view_name = Field(str, 'Content View')
