import logging
import time

from funcy import chunks

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, PLUGIN_NAME
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
                                      https_proxy=client_config.get('https_proxy'),
                                      domain_preferred=client_config.get('domain_preferred')) as connection:
            results = {}
            for internal_axon_ids_chunk in chunks(1000, internal_axon_ids):
                users = list(self.users_db.find({
                    'internal_axon_id': {'$in': internal_axon_ids_chunk}
                }, projection={
                    'internal_axon_id': 1,
                    f'adapters.{PLUGIN_UNIQUE_NAME}': 1,
                    f'adapters.{PLUGIN_NAME}': 1,
                    'adapters.data.id': 1,
                    'adapters.data.mail': 1,
                    'tags.data.mail': 1
                }))

                for user in users:
                    id_ = user.get('internal_axon_id')
                    if not id_:
                        continue
                    try:
                        internal_axon_id, result = self._handle_user(
                            user, connection,
                            client_config.get('alternative_suffix'), client_config.get('domain_whitelist')
                        )
                        results[internal_axon_id] = result
                    except Exception as e:
                        logger.exception(f'Error handling internal axon id {id_}')
                        results[id_] = {'success': False, 'value': str(e)}

        # What we have not found, is due to correlations probably
        for id_ in internal_axon_ids:
            if not results.get(id_):
                results[id_] = {'success': False, 'value': f'Internal axon id {id_} not found'}
        logger.info('Haveibeenpwned Trigger end.')
        return results

    @staticmethod
    def _get_enrichment_emails(user: dict) -> list:
        """ find all ips to use for the device enrichment """

        all_mails = set()
        for entity_type in ['adapters', 'tags']:
            for entity in (user.get(entity_type) or []):
                data = entity.get('data')
                if not isinstance(data, dict):
                    continue

                mail = data.get('mail')
                if mail and isinstance(mail, str):
                    all_mails.add(mail.strip())

        return list(all_mails)

    @staticmethod
    def _get_enrichment_client_id(id_, email):
        return '_'.join(('haveibeenpwnedenrichment', id_, email))

    def _handle_email(self, user: dict, email, connection):
        try:
            client_id = self._get_enrichment_client_id(user['internal_axon_id'], email)
            start = time.time()
            user_data = connection.get_breach_account_info(email)
            logger.debug(f'Took {int(time.time() - start)} seconds to query {email}')

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
            logger.debug(f'Failed to fetch email info for {email}, {e}', exc_info=True)
            return False

    def _handle_user(self, user: dict, connection, alternative_suffix: str = None, domain_whitelist: str = None):
        try:
            emails = self._get_enrichment_emails(user)
            if not emails:
                json = {'success': False, 'value': 'Haveibeenpwned Error: Missing Email'}
                return user['internal_axon_id'], json

            if domain_whitelist and isinstance(domain_whitelist, str):
                domain_whitelist = [domain.strip() for domain in domain_whitelist.split(',')]
                emails = [email for email in emails if any(email.endswith(item) for item in domain_whitelist)]

                if not emails:
                    json = {'success': False,
                            'value': 'Haveibeenpwned Error: No mails left after domain whitelist filtering'}
                    return user['internal_axon_id'], json

            if not alternative_suffix or not isinstance(alternative_suffix, str):
                alternative_suffix_list = []
            else:
                alternative_suffix_list = alternative_suffix.split(',')
            emails_full = emails.copy()
            for email_str in emails:
                for alternative_suffix_str in alternative_suffix_list:
                    emails_full.append(email_str.split('@')[0] + '@' + alternative_suffix_str)

            if not any([self._handle_email(user, email, connection) for email in emails_full]):
                return user['internal_axon_id'], {'success': True, 'value': 'Haveibeenpwned Enrichment - no breaches'}

            return user['internal_axon_id'], {'success': True, 'value': 'Haveibeenpwned Enrichment success'}
        except Exception as e:
            logger.exception('Exception while handling devices')
            return user['internal_axon_id'], {'success': False, 'value': f'Haveibeenpwned Enrichment Error: {str(e)}'}

    def _correlate_enrichment_if_needed(self, user: dict, new_user):
        try:
            for adapter in (user.get('adapters') or []):
                if adapter.get(PLUGIN_NAME) == 'haveibeenpwned_adapter' and isinstance(adapter.get('data'), dict):
                    if new_user['id'] in (adapter.get('data') or {}).get('id'):
                        # If id is in the "old" user id so this users are already correlated
                        # no need to correlate again.
                        return

            logger.debug('Correlating enrichment')
            first_plugin_unique_name = user['adapters'][0][PLUGIN_UNIQUE_NAME]
            first_user_adapter_id = user['adapters'][0]['data']['id']
            new_user_id = new_user['id']

            associated_adapters = [(first_plugin_unique_name, first_user_adapter_id),
                                   (self.plugin_unique_name, new_user_id)]

            correlation = CorrelationResult(associated_adapters=associated_adapters,
                                            data={'reason': 'Haveibeenpwned Enrichment'},
                                            reason=CorrelationReason.HaveibeenpwnedEnrichment)

            self.link_adapters(EntityType.Users, correlation)
        except Exception as e:
            logger.exception('Failed to correlate')
