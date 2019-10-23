import logging

from typing import Tuple, List

from axonius.consts.plugin_consts import PLUGIN_NAME
from axonius.entities import EntityType
from axonius.mixins.triggerable import RunIdentifier, Triggerable
from axonius.utils.db_querying_helper import iterate_axonius_entities

logger = logging.getLogger(f'axonius.{__name__}')

ACTION_TYPES = ['change_ldap_attributes']


class ActiveDirectoryExecutionMixIn(Triggerable):
    """
    This class handles Active Directory Trigger actions.
    Currently the supported action is change_ldap_attributes
    """

    def get_ad_id_by_entity(self, entity: dict) -> str:
        """
        Get active directory adapter id from entity data
        :param entity: entity data
        :return: active directory adapter id
        """
        adapters = entity.get('adapters')
        if not adapters:
            return None
        for adapter in adapters:
            if adapter.get(PLUGIN_NAME) == self.plugin_name:
                data = adapter.get('data')
                if data:
                    return data.get('id')
        return None

    def change_entity_ldap_attribute(self, entity: dict, ldap_attributes: List[dict], credentials: dict) \
            -> Tuple[str, dict]:
        """
        Change ldap attribute of an entity
        :param entity: entity data
        :param ldap_attributes: list of ldap attributes dict. keys: [attribute_name, attribute_value]
        :param attribute_value: value of the attribute
        :param credentials: custom credentials
        :return: axonius_id and action json response
        """
        dev_id = self.get_ad_id_by_entity(entity)
        axon_id = str(entity.get('internal_axon_id'))
        if not dev_id or not axon_id:
            json = {
                'success': False,
                'value': f'Error: {axon_id} does not have an active directory adapter data'
            }
            return axon_id, json
        status = False
        value = ''
        for attr in ldap_attributes:
            attribute_name = attr.get('attribute_name')
            attribute_value = attr.get('attribute_value')
            try:
                self.change_ldap_attribute_data(dev_id, attribute_name, attribute_value, credentials)
                value += f'Success - {attribute_name} : {attribute_value};'
                status = True
            except Exception as e:
                value += f'Error, {e} - {attribute_name} : {attribute_value};'

        json = {'success': status, 'value': value}
        return axon_id, json

    def _handle_trigger(self, post_json: dict):
        results = {}
        try:
            internal_axon_ids = post_json['internal_axon_ids']
            client_config = post_json['client_config']
            credentials = post_json['credentials']
            entity = post_json['entity']
            if not client_config:
                logger.info(f'Bad config {client_config}')
                return {
                    'status': 'error',
                    'message': f'Argument Error: Please specify valid Username and Key/Password'
                }
        except Exception as e:
            logger.exception(f'LDAP Argument error: {e}')
            return {
                'status': 'error',
                'message': f'Argument Error: {e}'
            }
        ldap_attributes = client_config.get('ldap_attributes')
        if not ldap_attributes:
            return {
                'status': 'error',
                'message': f'Error: No LDAP attributes'
            }
        try:
            entities = iterate_axonius_entities(EntityType(entity), internal_axon_ids)
            for ent in entities:
                try:
                    axon_id, json = self.change_entity_ldap_attribute(ent, ldap_attributes, credentials)
                    if axon_id in internal_axon_ids:
                        internal_axon_ids.remove(axon_id)
                    results[axon_id] = json
                except Exception:
                    logger.exception('Error changing ldap attribute')

            # this should never happen
            for _id in internal_axon_ids:
                results[_id] = {
                    'success': False,
                    'value': f'Entity {_id} not found'
                }
        except Exception as e:
            logger.exception(f'LDAP Error: {e}')
            return {
                'status': 'error',
                'message': f'Error: {e}'
            }
        return results

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name not in ACTION_TYPES:
            return super()._triggered(job_name, post_json, run_identifier, *args)
        logger.info(f'{job_name} was Triggered.')
        results = self._handle_trigger(post_json)
        logger.info(f'{job_name} Trigger end.')
        return results
