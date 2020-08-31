"""
Custom enrichments for AWS
"""
import logging
from typing import Dict

from aws_adapter.connection.structures import AWSAdapter
from axonius.plugin_base import PluginBase
from axonius.utils.dynamic_fields import put_dynamic_field

logger = logging.getLogger(f'axonius.{__name__}')


def get_firebom_data(plugin_base: PluginBase) -> Dict:
    service_team_name_to_service_team = plugin_base.get_global_keyval(
        'firebom_service_team_name_to_service_team'
    )
    service_team_name_to_service_instance = plugin_base.get_global_keyval(
        'firebom_service_team_name_to_service_instance'
    )
    account_id_to_service_team_name = plugin_base.get_global_keyval(
        'firebom_account_id_to_service_team_name'
    )

    if not service_team_name_to_service_team or not service_team_name_to_service_instance or \
            not account_id_to_service_team_name:
        return {}

    return {
        'service_team_name_to_service_team': service_team_name_to_service_team,
        'service_team_name_to_service_instance': service_team_name_to_service_instance,
        'account_id_to_service_team_name': account_id_to_service_team_name
    }


def append_firebom(entity: AWSAdapter, firebom_data: dict):
    account_id = entity.get_field_safe('aws_account_id')
    if not account_id:
        return

    account_id_to_service_team_name = firebom_data.get('account_id_to_service_team_name')
    service_team_name_to_service_team = firebom_data.get('service_team_name_to_service_team')
    service_team_name_to_service_instance = firebom_data.get('service_team_name_to_service_instance')

    all_service_team_names = account_id_to_service_team_name.get(str(account_id))
    if not all_service_team_names:
        return

    all_service_teams = []
    all_service_instances = []

    for service_team_name in all_service_team_names:
        service_team = service_team_name_to_service_team.get(service_team_name)
        if service_team:
            all_service_teams.append(service_team)

        service_instance = service_team_name_to_service_instance.get(service_team_name)
        if service_instance:
            all_service_instances.extend(service_instance)

    if all_service_teams:
        put_dynamic_field(entity, 'firebom_service_teams', all_service_teams, 'Firebom Service Teams')
    else:
        try:
            entity.firebom_service_teams = []
        except Exception:
            pass

    if all_service_instances:
        put_dynamic_field(entity, 'firebom_service_instances', all_service_instances, 'Firebom Service Instances')
    else:
        try:
            entity.firebom_service_instances = []
        except Exception:
            pass
