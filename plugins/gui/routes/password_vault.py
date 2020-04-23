import logging

from axonius.plugin_base import return_error
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction, PermissionValue

from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
# pylint: disable=no-member,inconsistent-return-statements

logger = logging.getLogger(f'axonius.{__name__}')


@gui_category_add_rules()
class PasswordVault:
    #################
    # Vault Service #
    #################

    @gui_route_logged_in('password_vault', methods=['POST'], required_permission=PermissionValue.get(
        PermissionAction.Update, PermissionCategory.Adapters))
    def check_password_vault_query(self):
        """
        Checks if the query successfully fetches data from requested vault
        (for use before saving the client credentials).
        :return: True if successfully retrieves data from requested vault.
        """
        vault_fetch_data = self.get_request_data_as_object()
        try:
            if self.check_password_fetch(vault_fetch_data['field'], vault_fetch_data['query']):
                return ''
        except Exception as exc:
            return return_error(str(exc), non_prod_error=True, http_status=500)
