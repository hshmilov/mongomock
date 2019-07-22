import logging

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.mixins.triggerable import RunIdentifier, Triggerable
from axonius.plugin_base import EntityType
from axonius.types.correlation import CorrelationReason, CorrelationResult
from axonius.utils.gui_helpers import find_entity_field
from axonius.clients.haveibeenpwned.connection import HaveibeenpwnedConnection
logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=too-many-branches


def get_entity_field_list(device_data, field):
    """" find_entity_field returns object when single
         field exist and list when multiple objects exist.
         it hard to work like this, so this wrapper always returns a list """

    result = find_entity_field(device_data, field)
    if result is None:
        return []
    if not isinstance(result, list):
        result = [result]
    return result


class HaveibeenpwnedExecutionMixIn(Triggerable):
    @staticmethod
    def get_valid_config(config):
        try:
            required_args = ['verify_ssl', 'apikey']
            if not all(arg in config for arg in required_args):
                logger.error(f'Malformed config. Not running: {str(config)}')
                return None
        except Exception:
            logger.exception('Error when preparing arguments')
            return None
        return config

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name != 'enrich':
            return super()._triggered(job_name, post_json, run_identifier, *args)

        logger.info('Haveibeenpwned was Triggered.')
        internal_axon_ids = post_json['internal_axon_ids']
        client_config = post_json['client_config']
        if not client_config:
            logger.debug(f'Bad config {client_config}')
            return {'status': 'error', 'message': f'Argument Error: Please specify a valid email'}
        with HaveibeenpwnedConnection(verify_ssl=client_config.get('verify_ssl'), apikey=client_config.get('apikey'),
                                      https_proxy=client_config.get('https_proxy')) as connection:
            results = {}
            for id_ in internal_axon_ids:
                user = list(self.users.get(internal_axon_id=id_))[0]
                internal_axon_id, result = self._handle_user(user, connection)
                results[internal_axon_id] = result
        logger.info('Haveibeenpwned Trigger end.')
        return results

    @staticmethod
    def _get_enrichment_emails(user):
        """ find all ips to use for the device enrichment """

        mails = get_entity_field_list(user.data, 'specific_data.data.mail')

        return mails

    @staticmethod
    def _get_enrichment_client_id(id_, email):
        return '_'.join(('haveibeenpwnedenrichment', id_, email))

    def _handle_email(self, user, email, connection):
        try:
            client_id = self._get_enrichment_client_id(user.internal_axon_id, email)
            user_data = connection.get_breach_account_info(email)

            new_user = self._create_user(user_data, email)

            # Here we create a new user adapter tab out of cycle
            self._save_data_from_plugin(client_id,
                                        {'raw': [], 'parsed': [new_user.to_dict()]},
                                        EntityType.Users,
                                        False)

            self._save_field_names_to_db(EntityType.Users)
            self._correlate_enrichment_if_needed(user, new_user)
            return True
        except Exception as e:
            logger.warning(f'Failed to fetch email info for {email}, {e}', exc_info=True)
            return False

    def _handle_user(self, user, connection):
        try:
            if not user.specific_data:
                json = {'success': False, 'value': 'Haveibeenpwned Error: Adapters not found'}
                return (user.internal_axon_id, json)

            emails = self._get_enrichment_emails(user)
            if not emails:
                json = {'success': False, 'value': 'Haveibeenpwned Error: Missing Email'}
                return (user.internal_axon_id, json)

            if not any([self._handle_email(user, email, connection) for email in emails]):
                return (user.internal_axon_id, {'success': False, 'value': 'Haveibeenpwned Enrichment - no results'})

            return (user.internal_axon_id, {'success': True, 'value': 'Haveibeenpwned Enrichment success'})
        except Exception as e:
            logger.exception('Exception while handling devices')
            return (user.internal_axon_id, {'success': False, 'value': f'Haveibeenpwned Enrichment Error: {str(e)}'})

    def _correlate_enrichment_if_needed(self, user, new_user):
        try:
            id_ = get_entity_field_list(user.data, 'adapters_data.haveibeenpwned_adapter.id')
            id_ = ''.join(id_)

            # If id is in the "old" user id so this users are already correlated
            # no need to correlate again.
            if new_user['id'] in id_:
                return

            logger.debug('Correlating enrichment')
            first_plugin_unique_name = user.specific_data[0][PLUGIN_UNIQUE_NAME]
            first_user_adapter_id = user.specific_data[0]['data']['id']
            new_user_id = new_user.id

            associated_adapters = [(first_plugin_unique_name, first_user_adapter_id),
                                   (self.plugin_unique_name, new_user_id)]

            correlation = CorrelationResult(associated_adapters=associated_adapters,
                                            data={'reason': 'Haveibeenpwned Enrichment'},
                                            reason=CorrelationReason.HaveibeenpwnedEnrichment)

            self.link_adapters(EntityType.Users, correlation)
        except Exception as e:
            logger.exception('Failed to correlate')
