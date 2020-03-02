import datetime

from axonius.utils.parsing import format_ip
from axonius.smart_json_class import SmartJsonClass
from axonius.fields import Field, ListField, JsonStringFormat


class AzureInstance(SmartJsonClass):
    pass  # TBD


# pylint: disable=too-many-instance-attributes
class AwsInstance(SmartJsonClass):
    state = Field(str, 'State',
                  description='Endpoint state.')
    attached_ebs = Field(int, 'Total EBS Size',
                         description='Attached Elastic Block Store.')
    launch_date = Field(datetime.datetime, 'Launch Date',
                        description='Launch date.')
    price_per_month = Field(str, 'Price Per Month',
                            description='Endpoint price per month.')
    total_cost_per_month = Field(str, 'Total Cost Per Month',
                                 description='Endpoint cost per month.')
    current_projected_cost = Field(str, 'Current Projected Cost',
                                   description='Endpoint projected cost currently.')
    hourly_cost = Field(str, 'Hourly Cost',
                        description='Endpoint cost per hour.')
    key = Field(str, 'Key',
                description='Endpoint key.')
    is_monitored = Field(bool, 'Monitored',
                         description='Does endpoint monitored.')
    is_spot = Field(bool, 'Spot',
                    description='Does endpoint being spot.')
    is_ebs_optimized = Field(bool, 'Optimized EBS',
                             description='Optimized EBS.')
    root_device_name = Field(str, 'Root Device Name',
                             description='Root device name.')
    root_device_type = Field(str, 'Root Device Type',
                             description='Root device type.')
    virtualization_type = Field(str, 'Virtualization Type',
                                description='Virtualization type.')
    owner_email = Field(str, 'Owner Email',
                        description='Owner email.')
    hypervisor = Field(str, 'Hypervisor',
                       description='Hypervisor.')
    private_ip = ListField(str, 'Private IP\'s,', converter=format_ip, json_format=JsonStringFormat.ip,
                           description='Private ip\'s.')
    public_dns = ListField(str, 'Public DNS',
                           description='Public DNS.')
    private_dns = ListField(str, 'Private DNS',
                            description='Private DNS.')
