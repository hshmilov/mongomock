import logging
from collections import defaultdict
from typing import Tuple

from aws_adapter.connection.structures import AWSDeviceAdapter, AWSRoute53Record

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-nested-blocks
def query_devices_by_client_by_source_route53(client_data: dict) -> dict:
    route53_client = client_data.get('route53')
    if route53_client is not None:
        try:
            for route53_hosted_zone_answer in route53_client.get_paginator('list_hosted_zones').paginate():
                for hosted_zone_raw in (route53_hosted_zone_answer.get('HostedZones') or []):
                    hosted_zone_id = hosted_zone_raw.get('Id')
                    dns_records_for_zone = defaultdict(list)
                    if not hosted_zone_id:
                        logger.warning(f'hosted zone with no id {hosted_zone_raw}')
                        continue
                    for route53_resource_record_sets_answer in route53_client.get_paginator(
                            'list_resource_record_sets').paginate(HostedZoneId=hosted_zone_id):
                        for resource_record_set_raw in (
                                route53_resource_record_sets_answer.get('ResourceRecordSets') or []):
                            resource_name = resource_record_set_raw.get('Name')
                            if not resource_name:
                                logger.warning(f'No resource name for route53 resource: {resource_record_set_raw}')
                                continue

                            dns_records_for_zone[resource_name].append(resource_record_set_raw)

                    # Yield all the dns records for this zone. Notice that a couple of records with the same
                    # name can resize in the same zone. This happens when there is weight affects.
                    for dns_name, dns_info in dns_records_for_zone.items():
                        yield dns_name, dns_info, hosted_zone_raw
        except Exception:
            logger.exception(f'Problem fetching data for route53')


def parse_raw_data_inner_route53(
        device: AWSDeviceAdapter,
        raw_data_all: Tuple[str, list, dict],
) -> AWSDeviceAdapter:
    dns_name, device_data, zone_info = raw_data_all
    dns_name = dns_name.strip('.')
    device.id = 'aws-route53-' + zone_info['Id'] + '-' + dns_name
    device.cloud_provider = 'AWS'
    device.cloud_id = dns_name
    device.aws_device_type = 'Route53'
    device.hostname = dns_name
    device.name = dns_name
    device.dns_names.append(dns_name)

    device.route53_zone_id = zone_info['Id']
    device.route53_zone_name = zone_info.get('Name')
    zone_config = zone_info.get('Config') or {}
    device.route53_zone_is_private = zone_config.get('PrivateZone') \
        if isinstance(zone_config.get('PrivateZone'), bool) else None

    for record_raw in device_data:
        evaluate_target_health = (record_raw.get('AliasTarget') or {}).get('EvaluateTargetHealth')
        resource_records = [
            str(resource_record.get('Value')).strip('.')
            for resource_record in (record_raw.get('ResourceRecords') or []) if resource_record.get('Value')
        ]

        if str(record_raw.get('Type')).upper() in ['A', 'AAAA']:
            try:
                device.add_ips_and_macs(ips=resource_records)
            except Exception:
                logger.exception(f'Problem adding IPs for route53 record {record_raw}')

        if str(record_raw.get('Type')).upper() == 'CNAME':
            device.dns_names.extend(resource_records)

        alias_target_dns_name = (record_raw.get('AliasTarget') or {}).get('DNSName')
        if alias_target_dns_name:
            stripped_dns_name = alias_target_dns_name
            if stripped_dns_name.startswith('dualstack'):
                stripped_dns_name = stripped_dns_name[len('dualstack'):]
            stripped_dns_name = stripped_dns_name.strip('.')
            device.dns_names.append(stripped_dns_name)

        device.route53_data.append(
            AWSRoute53Record(
                resource_type=record_raw.get('Type'),
                ttl=record_raw.get('TTL') if isinstance(record_raw.get('TTL'), int) else None,
                set_identifier=record_raw.get('SetIdentifier'),
                weight=record_raw.get('Weight') if isinstance(record_raw.get('Weight'), int) else None,
                region=record_raw.get('Region'),
                geo_location_continent_code=(record_raw.get('GeoLocation') or {}).get('ContinentCode'),
                geo_location_country_code=(record_raw.get('GeoLocation') or {}).get('CountryCode'),
                geo_location_subdivision_code=(record_raw.get('GeoLocation') or {}).get('SubdivisionCode'),
                failover=record_raw.get('Failover'),
                multi_value_answer=record_raw.get('MultiValueAnswer') if isinstance(
                    record_raw.get('MultiValueAnswer'), bool) else None,
                health_check_id=record_raw.get('HealthCheckId'),
                traffic_policy_instance_id=record_raw.get('TrafficPolicyInstanceId'),
                resource_records=resource_records if resource_records else None,
                alias_target_hosted_zone_id=(record_raw.get('AliasTarget') or {}).get('HostedZoneId'),
                alias_target_dns_name=alias_target_dns_name,
                alias_target_evaluate_target_health=evaluate_target_health if isinstance(
                    evaluate_target_health, bool) else None
            )
        )

    device.set_raw({'zone_info': zone_info, 'records': device_data})
    return device
