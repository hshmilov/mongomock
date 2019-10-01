import re
import logging
from axonius.correlator_engine_base import CorrelatorEngineBase
from axonius.correlator_base import does_entity_have_field


from axonius.entities import EntityType
from axonius.types.correlation import CorrelationReason

logger = logging.getLogger(f'axonius.{__name__}')

NORMALIZED_MAIL = 'normalized_mail'
BAD_USER_NAMES = ['NULL NULL']


def get_ad_upn(adapter_data):
    ad_upn = adapter_data['data'].get('ad_user_principal_name')
    if ad_upn:
        return ad_upn.lower().strip()
    return None


def get_aws_username(adapter_data):
    if adapter_data.get('plugin_name') == 'aws_adapter' and get_username(adapter_data):
        return get_username(adapter_data)
    return None


def get_username(adapter_data):
    username = adapter_data['data'].get('username')
    if username and username not in BAD_USER_NAMES:
        return username.lower().strip()
    return None


def get_username_prefix(adapter_data):
    username = get_username(adapter_data)
    if not username:
        return None
    return username.split('@')[0]


def compare_username_prefix(adapter_data1, adapter_data2):
    username_1 = get_username_prefix(adapter_data1)
    username_2 = get_username_prefix(adapter_data2)
    if not username_1 or not username_2:
        return True
    return username_1 == username_2


def compare_username(adapter_data1, adapter_data2):
    username_1 = get_username(adapter_data1)
    username_2 = get_username(adapter_data2)
    if not username_1 or not username_2:
        return True
    return username_1 == username_2


def get_ad_display_name(adapter_data):
    ad_display_name = adapter_data['data'].get('ad_display_name')
    if ad_display_name and ad_display_name.lower().strip() not in ['unknown']:
        return ad_display_name.lower().strip()
    return None


def get_ad_display_name_username(adapter_data):
    ad_display_name = get_ad_display_name(adapter_data)
    if ad_display_name:
        return ad_display_name
    username = get_username(adapter_data)
    if username:
        return username
    return None


def get_user_domain(adapter_data):
    user_domain = adapter_data['data'].get('domain')
    if user_domain:
        return user_domain.lower().strip()
    return None


def domain_do_not_contradict(adapter_data1, adapter_data2):
    domain_1 = get_user_domain(adapter_data1)
    domain_2 = get_user_domain(adapter_data2)
    if not domain_1 or not domain_2:
        return True
    return domain_1 == domain_2


def compare_ad_display_name_username(adapter_data1, adapter_data2):
    ad_display_name_username1 = get_ad_display_name_username(adapter_data1)
    ad_display_name_username2 = get_ad_display_name_username(adapter_data2)
    if ad_display_name_username1 and ad_display_name_username2:
        return ad_display_name_username1 == ad_display_name_username2
    return False


def get_ad_upn_mail(adapter_data):
    ad_upn = get_ad_upn(adapter_data)
    if ad_upn:
        return ad_upn
    email = adapter_data.get(NORMALIZED_MAIL)
    if email:
        return email
    return None


def get_aws_username_mail(adapter_data):
    aws_username = get_aws_username(adapter_data)
    if aws_username:
        return aws_username
    email = adapter_data.get(NORMALIZED_MAIL)
    if email:
        return email
    return None


def compare_aws_username_mail(adapter_data1, adapter_data2):
    aws_username_1_mail = get_aws_username_mail(adapter_data1)
    aws_username_2_mail = get_aws_username_mail(adapter_data2)
    if aws_username_1_mail and aws_username_2_mail and aws_username_1_mail == aws_username_2_mail:
        return True
    return False


def compare_ad_display_name(adapter_data1, adapter_data2):
    ad_display_name1 = get_ad_display_name(adapter_data1)
    ad_display_name2 = get_ad_display_name(adapter_data2)
    if ad_display_name1 and ad_display_name2:
        return ad_display_name1 == ad_display_name2
    return False


def compare_ad_upn(adapter_data1, adapter_data2):
    ad_upn_1 = get_ad_upn(adapter_data1)
    ad_upn_2 = get_ad_upn(adapter_data2)
    if ad_upn_1 and ad_upn_2 and ad_upn_1 == ad_upn_2:
        return True
    return False


def compare_ad_upn_mail(adapter_data1, adapter_data2):
    ad_upn_1_mail = get_ad_upn_mail(adapter_data1)
    ad_upn_2_mail = get_ad_upn_mail(adapter_data2)
    if ad_upn_1_mail and ad_upn_2_mail and ad_upn_1_mail == ad_upn_2_mail:
        return True
    return False


def compare_mail_prefix(adapter_user1, adapter_user2):
    return get_mail_prefix(adapter_user1) and get_mail_prefix(adapter_user2) and\
        get_mail_prefix(adapter_user1) == get_mail_prefix(adapter_user2)


def get_mail_prefix(adapter_user):
    mail = adapter_user.get(NORMALIZED_MAIL)
    if mail and len(mail.split('@')) > 1:
        return mail.split('@')[0]
    return None


def compare_mail(adapter_user1, adapter_user2):
    return adapter_user1.get(NORMALIZED_MAIL) and\
        adapter_user1.get(NORMALIZED_MAIL) == adapter_user2.get(NORMALIZED_MAIL)


def has_email(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: adapter_data.get('mail'))  # not none


def has_principle_name(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: adapter_data.get('ad_user_principal_name'))  # not none


def has_username(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: adapter_data.get('username'))  # not none


def has_ad_display_name(adapters):
    return does_entity_have_field(adapters, lambda adapter_data: adapter_data.get('ad_display_name'))  # not none


def normalize_mail(adapter_data):
    mail = adapter_data.get('mail')
    if not mail:
        # Check if we have Active Directory principle name instead
        mail = adapter_data.get('ad_user_principal_name')
        if not mail:
            return None
    # Checking mail format validity
    if not re.match(r'[^@]+@[^@]+\.[^@]+', mail):
        logger.debug(f'Unrecognized email format found: {mail}')
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
        return [has_email, has_principle_name, has_username, has_ad_display_name]

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

    def _correlate_ad_upn_mail(self, entities):
        logger.info('Starting to correlate on ad upn mail')
        filtered_adapters_list = filter(get_ad_upn_mail, entities)
        yield from self._bucket_correlate(list(filtered_adapters_list),
                                          [get_ad_upn_mail],
                                          [compare_ad_upn_mail],
                                          [],
                                          [],
                                          {'Reason': 'They have the same ad upn mail'},
                                          CorrelationReason.StaticAnalysis)

    def _correlate_aws_username_mail(self, entities):
        logger.info('Starting to correlate on aws username mail')
        filtered_adapters_list = filter(get_aws_username_mail, entities)
        yield from self._bucket_correlate(list(filtered_adapters_list),
                                          [get_aws_username_mail],
                                          [compare_aws_username_mail],
                                          [],
                                          [],
                                          {'Reason': 'They have the same mail plus AWS username'},
                                          CorrelationReason.StaticAnalysis)

    def _correlate_email_prefix(self, entities):
        logger.info('Starting to correlate on mail prefix')
        mails_indexed = {}
        for adapter in entities:
            email = adapter.get(NORMALIZED_MAIL)
            if email and len(email.split('@')) > 1:
                email_prefix = email.split('@')[0]
                mails_indexed.setdefault(email_prefix, []).append(adapter)
        for matches in mails_indexed.values():
            if len(matches) >= 2:
                yield from self._bucket_correlate(matches,
                                                  [],
                                                  [],
                                                  [],
                                                  [compare_mail_prefix],
                                                  {'Reason': 'They have the same mail prefix'},
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

    def _correlate_username_aws(self, entities):
        logger.info('Starting to correlate on aws username')
        filtered_adapters_list = filter(get_username_prefix, entities)
        yield from self._bucket_correlate(list(filtered_adapters_list),
                                          [get_username_prefix],
                                          [compare_username_prefix],
                                          [get_aws_username],
                                          [],
                                          {'Reason': 'They have the same username and one is AWS'},
                                          CorrelationReason.StaticAnalysis)

    def _correlate_ad_display_name(self, entities):
        """
        Correlate Azure AD and AD
        """
        logger.info('Starting to correlate on AD Display')
        filtered_adapters_list = filter(get_ad_display_name, entities)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_ad_display_name],
                                      [compare_ad_display_name],
                                      [],
                                      [domain_do_not_contradict],
                                      {'Reason': 'They have the same AD display name'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_ad_display_name_username(self, entities):
        """
        Correlate Azure AD and AD
        """
        logger.info('Starting to correlate on AD Display + username')
        filtered_adapters_list = filter(get_ad_display_name_username, entities)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_ad_display_name_username],
                                      [compare_ad_display_name_username],
                                      [],
                                      [domain_do_not_contradict],
                                      {'Reason': 'They have the same AD display name- username'},
                                      CorrelationReason.StaticAnalysis)

    def _raw_correlate(self, entities):
        yield from self._correlate_mail(normalize_adapter_users(entities))
        yield from self._correlate_ad_upn(normalize_adapter_users(entities))
        yield from self._correlate_ad_upn_mail(normalize_adapter_users(entities))
        yield from self._correlate_ad_display_name(normalize_adapter_users(entities))
        yield from self._correlate_ad_display_name_username(normalize_adapter_users(entities))
        yield from self._correlate_aws_username_mail(normalize_adapter_users(entities))
        yield from self._correlate_username_aws(normalize_adapter_users(entities))
        if self._correlation_config and self._correlation_config.get('email_prefix_correlation') is True:
            yield from self._correlate_email_prefix(normalize_adapter_users(entities))
