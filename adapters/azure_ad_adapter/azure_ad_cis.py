"""
Azure AD Cis helpers
"""
# pylint: disable=too-many-branches
import logging

from axonius.clients.azure.structures import AzureAdapterEntity
logger = logging.getLogger(f'axonius.{__name__}')


def append_azure_cis_data_to_device(device: AzureAdapterEntity):
    """
    XXX Nothing to do
    :param device:
    :return:
    """
    return


def append_azure_cis_data_to_user(user: AzureAdapterEntity):
    """
    Check for rule 1.3 (user is guest), add that rule.
    Currently does not support rule 1.23 because subscription owner roles
    are not parsed into azure ad user data.
    :param user: AzureAdAdapter.MyUserAdapter instance
    """
    if 'guest' in str(user.get_field_safe('user_type')).lower():
        user.add_azure_cis_incompliant_rule('1.3')
