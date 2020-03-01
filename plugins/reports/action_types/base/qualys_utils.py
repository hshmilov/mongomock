import functools
import logging
from typing import Dict, Generator, Iterable

from axonius.clients.qualys import consts
from axonius.types.enforcement_classes import EntityResult

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'qualys_scans_adapter'
ACTION_CONFIG_TAGS = 'tags_list'


class QualysActionUtils:

    GENERAL_CONFIG_SCHEMA = {
        'items': [
            {'name': consts.QUALYS_SCANS_DOMAIN, 'title': 'Qualys Cloud Platform domain', 'type': 'string'},
            {'name': consts.USERNAME, 'title': 'User name', 'type': 'string'},
            {'name': consts.PASSWORD, 'title': 'Password', 'type': 'string', 'format': 'password'},
            {'name': consts.VERIFY_SSL, 'title': 'Verify SSL', 'type': 'bool'},
            {'name': consts.HTTPS_PROXY, 'title': 'HTTPS proxy', 'type': 'string'},
            {'name': ACTION_CONFIG_TAGS, 'title': 'Tags', 'type': 'array', 'items': {'type': 'string'}},
        ],
        'required': [consts.QUALYS_SCANS_DOMAIN,
                     consts.USERNAME,
                     consts.PASSWORD,
                     consts.VERIFY_SSL,
                     ACTION_CONFIG_TAGS,
                     ],
        'type': 'array',
    }

    GENERAL_DEFAULT_CONFIG = {
        consts.QUALYS_SCANS_DOMAIN: '',
        consts.USERNAME: '',
        consts.PASSWORD: '',
        consts.VERIFY_SSL: False,
        consts.HTTPS_PROXY: None,
        ACTION_CONFIG_TAGS: [],
    }

    @staticmethod
    def get_axon_by_qualys_id_and_reject_invalid(current_result: Iterable[dict]) \
            -> Generator[EntityResult, None, Dict[str, str]]:

        valid_devices = {}

        for entry in current_result:
            axon_id = entry['internal_axon_id']
            qualys_id = (yield from map(functools.partial(EntityResult, axon_id, False),
                                        QualysActionUtils._extract_qualys_id_and_reject_invalid(entry)))
            if isinstance(qualys_id, str):
                valid_devices[qualys_id] = axon_id

        return valid_devices

    @staticmethod
    def _extract_qualys_id_and_reject_invalid(entry: dict) -> Generator[str, None, str]:

        try:
            # Retrieve Entry adapters list
            adapters_list = entry.get('adapters') or []
            if not adapters_list:
                return (yield f'Missing adapters')

            # Filter out non Qualys Scans adapters and make sure there are no more than 2
            qualys_adapter_list = list(filter(lambda adapter: (adapter.get('plugin_name') or '') == ADAPTER_NAME,
                                              adapters_list))
            if not qualys_adapter_list:
                return (yield f'Missing Qualys adapter')
            if len(qualys_adapter_list) > 1:
                return (yield f'Multiple Qualys adapter connections')
            qualys_adapter = qualys_adapter_list[0]

            # retrieve qualys id
            qualys_id = (qualys_adapter.get('data') or {}).get('qualys_id') or None
            if not isinstance(qualys_id, str):
                return (yield 'Missing Qualys ID')

            return qualys_id
        except Exception:
            logger.exception(f'Unexpected error occured during Qualys id extraction')

            return (yield 'Unexpected error during id extraction')
