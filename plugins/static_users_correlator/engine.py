import re
import logging
from axonius.correlator_engine_base import CorrelatorEngineBase
from axonius.correlator_base import does_entity_have_field

from axonius.entities import EntityType
from axonius.types.correlation import CorrelationReason

logger = logging.getLogger(f'axonius.{__name__}')

NORMALIZED_MAIL = 'normalized_mail'


def get_ad_upn(adapter_data):
    ad_upn = adapter_data['data'].get('ad_user_principal_name')
    if ad_upn:
        return ad_upn.lower().strip()
    return None


def compare_ad_upn(adapter_data1, adapter_data2):
    ad_upn_1 = get_ad_upn(adapter_data1)
    ad_upn_2 = get_ad_upn(adapter_data2)
    if ad_upn_1 and ad_upn_2 and ad_upn_1 == ad_upn_2:
        return True
    return False


def compare_mail(adapter_user1, adapter_user2):
    return adapter_user1.get(NORMALIZED_MAIL) and\
        adapter_user1.get(NORMALIZED_MAIL) == adapter_user2.get(NORMALIZED_MAIL)


def has_email(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: adapter_data.get('mail'))  # not none


def has_principle_name(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: adapter_data.get('ad_user_principal_name'))  # not none


def normalize_mail(adapter_data):
    mail = adapter_data.get('mail')
    if not mail:
        # Check if we have Active Directory principle name instead
        mail = adapter_data.get('ad_user_principal_name')
        if not mail:
            return None
    # Checking mail format validity
    if not re.match(r'[^@]+@[^@]+\.[^@]+', mail):
        logger.warning(f'Unrecognized email format found: {mail}')
        return None

    return mail.strip().lower()


def normalize_adapter_user(adapter_user):
    adapter_data = adapter_user['data']
    adapter_user[NORMALIZED_MAIL] = normalize_mail(adapter_data)
    return adapter_user


def normalize_adapter_users(users):
    """
    Normalized mail of users
    :param users: all of the users to be correlated
    :return: a normalized list of the adapter_users
    """
    for user in users:
        for adapter_user in user['adapters']:
            yield normalize_adapter_user(adapter_user)
        for tag in user.get('tags', []):
            if tag.get('entity') == EntityType.Users.value and \
                    tag.get('type') == 'adapterdata' and \
                    tag.get('associated_adapter_plugin_name') and \
                    len(tag.get('associated_adapters', [])) == 1:
                yield normalize_adapter_user(tag)


class StaticUserCorrelatorEngine(CorrelatorEngineBase):
    @property
    def _correlation_preconditions(self):
        return [has_email, has_principle_name]

    def _correlate_ad_upn(self, entities):
        logger.info('Starting to correlate on ad upn')
        filtered_adapters_list = filter(get_ad_upn, entities)
        yield from self._bucket_correlate(list(filtered_adapters_list),
                                          [get_ad_upn],
                                          [compare_ad_upn],
                                          [],
                                          [],
                                          {'Reason': 'They have the same ad upn'},
                                          CorrelationReason.StaticAnalysis)

    def _correlate_mail(self, entities):
        logger.info('Starting to correlate on mail')
        mails_indexed = {}
        for adapter in entities:
            email = adapter.get(NORMALIZED_MAIL)
            if email:
                mails_indexed.setdefault(email, []).append(adapter)
        for matches in mails_indexed.values():
            if len(matches) >= 2:
                yield from self._bucket_correlate(matches,
                                                  [],
                                                  [],
                                                  [],
                                                  [compare_mail],
                                                  {'Reason': 'They have the same mail'},
                                                  CorrelationReason.StaticAnalysis)

    def _raw_correlate(self, entities):
        yield from self._correlate_mail(normalize_adapter_users(entities))
        yield from self._correlate_ad_upn(normalize_adapter_users(entities))
