import logging

from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from reports.action_types.action_type_base import ActionTypeBase, generic_fail

logger = logging.getLogger(f'axonius.{__name__}')
USERNAME_MAGIC_WORD = '{{USERNAME}}'
FIRST_NAME_MAGIC_WORD = '{{FIRST_NAME}}'


class SendEmailToEntities(ActionTypeBase):

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'mail_subject',
                    'title': 'Mail Subject',
                    'type': 'string'
                },
                {
                    'name': 'mail_content',
                    'title': 'Mail Content',
                    'type': 'string',
                    'format': 'text'
                },
            ],
            'required': [
                'mail_subject',
                'mail_content'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'mail_content': None,
            'mail_subject': None,
        }

    def _run(self) -> EntitiesResult:
        mail_sender = self._plugin_base.mail_sender
        if not mail_sender:
            logger.info('Email cannot be sent because no email server is configured')
            return generic_fail(self._internal_axon_ids, reason='Email is disabled')
        current_result = self._get_entities_from_view({
            'adapters.data.mail': 1,
            'internal_axon_id': 1
        })
        results = []
        for entry in current_result:
            try:
                mail_content = self._config['mail_content']
                first_name = None
                username = None
                mail_list = set()
                for adapter_data in entry['adapters']:
                    adapter_data = adapter_data.get('data') or {}
                    if adapter_data.get('mail'):
                        mail_list.add(adapter_data.get('mail'))
                    if adapter_data.get('first_name') and not first_name:
                        first_name = adapter_data.get('first_name')
                    if adapter_data.get('username') and not username:
                        username = adapter_data.get('username')
                if username:
                    mail_content = mail_content.replace(USERNAME_MAGIC_WORD, username)
                if first_name:
                    mail_content = mail_content.replace(FIRST_NAME_MAGIC_WORD, first_name)
                mail_list = list(mail_list)
                email = mail_sender.new_email(self._config['mail_subject'], mail_list)
                email.send(mail_content)
                results.append(EntityResult(entry['internal_axon_id'], True, 'sucesss'))
            except Exception as e:
                logger.exception(f'Failed sending email to {entry}')
                results.append(EntityResult(entry['internal_axon_id'], False, f'Unexpected Error: {str(e)}'))
        return results
