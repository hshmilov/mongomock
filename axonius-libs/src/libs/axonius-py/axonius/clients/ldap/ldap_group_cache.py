import logging
from threading import Lock

import cachetools
from axonius.utils.threading import singlethreaded

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=W0212

def ldap_connection_identity(con: 'LdapConnection'):
    return con.domain_name


@singlethreaded(key_func=ldap_connection_identity)
@cachetools.cached(cachetools.TTLCache(maxsize=20, ttl=3600), key=ldap_connection_identity, lock=Lock())
def get_ldap_groups(con: 'LdapConnection'):
    logger.info(f'Initializing LDAP groups for the first time for {con.domain_name}')
    ldap_groups = {}
    ldap_groups_rsid_to_dn = {}
    groups = con._ldap_search('(objectClass=group)', attributes=['memberOf', 'distinguishedName', 'objectSid'])
    for group in groups:
        init_group_dn = group.get('distinguishedName')
        group_member_of = group.get('memberOf')
        object_sid = group.get('objectSid')

        if not init_group_dn:
            logger.error(f'Error, found group with no DN, continuing')
            continue

        if isinstance(group_member_of, str):
            group_member_of = [group_member_of]

        ldap_groups[init_group_dn] = {'search_mode': False}
        if group_member_of:
            ldap_groups[init_group_dn]['member_of'] = group_member_of

        if str(object_sid):
            rsid = str(object_sid).split('-')[-1]
            if rsid:
                ldap_groups_rsid_to_dn[rsid] = init_group_dn

    logger.info(f'Initiated LDAP groups successfully. number of groups: {len(ldap_groups)}')
    return ldap_groups, ldap_groups_rsid_to_dn
