import logging
import os
from datetime import datetime
from flask import (jsonify,
                   make_response)

from axonius.compliance.compliance import get_compliance

from axonius.consts.gui_consts import (FeatureFlagsNames, CloudComplianceNames, FILE_NAME_TIMESTAMP_FORMAT)
from axonius.plugin_base import return_error

from axonius.utils.gui_helpers import (Permission, PermissionLevel,
                                       PermissionType, accounts as accounts_filter,
                                       schema_fields as schema)
from gui.logic.entity_data import (get_export_csv)
from gui.logic.routing_helper import gui_add_rule_logged_in
# pylint: disable=no-member

logger = logging.getLogger(f'axonius.{__name__}')

SAML_SETTINGS_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config', 'saml_settings.json'))


class Compliance:

    @accounts_filter()
    @gui_add_rule_logged_in('compliance/<name>/<method>', methods=['GET', 'POST'],
                            required_permissions=[Permission(PermissionType.Devices, PermissionLevel.ReadOnly),
                                                  Permission(PermissionType.Users, PermissionLevel.ReadOnly)]
                            )
    def compliance(self, name, method, accounts):
        return self._get_compliance(name, method, accounts)

    def _get_compliance(self, name, method, accounts):
        try:
            if not self._is_compliance_visible():
                return return_error('Cloud asset compliance is not visible')
            return jsonify(get_compliance(name, method, accounts))
        except Exception as e:
            logger.exception(f'Error in get_compliance')
            return return_error(str(e), non_prod_error=True, http_status=500)

    @accounts_filter()
    @schema()
    @gui_add_rule_logged_in('compliance/<name>/csv', methods=['POST'],
                            required_permissions=[Permission(PermissionType.Devices, PermissionLevel.ReadOnly),
                                                  Permission(PermissionType.Users, PermissionLevel.ReadOnly)]
                            )
    def compliance_csv(self, name, schema_fields, accounts):
        return self._post_compliance_csv(name, schema_fields, accounts)

    def _post_compliance_csv(self, name, schema_fields, accounts):
        try:
            if not self._is_compliance_visible():
                return return_error('Cloud asset compliance is not visible')
            return self._get_compliance_rules_csv(name, schema_fields, accounts)
        except Exception as e:
            logger.exception(f'Error in get_compliance')
            return return_error(str(e), non_prod_error=True, http_status=500)

    def _is_compliance_visible(self):
        cloud_compliance_settings = self.feature_flags_config().get(FeatureFlagsNames.CloudCompliance) or {}
        is_cloud_compliance_visible = cloud_compliance_settings.get(CloudComplianceNames.Visible)
        return is_cloud_compliance_visible

    @staticmethod
    def _get_compliance_rules_csv(compliance_name, schema_fields, accounts):
        rules = get_compliance(compliance_name, 'report', accounts)

        def _get_order(elem):
            return elem.get('order')

        schema_fields.sort(key=_get_order)

        field_by_name = {
            field['name']: field for field in
            # show only the fields with 0 or more in the order attribute
            list(filter(lambda f: _get_order(f) >= 0, schema_fields))
        }
        # pylint: disable=unsupported-assignment-operation
        for rule in rules:
            rule['entities_results'] = rule.get('error') \
                if rule.get('error') else rule.get('entities_results')
        # pylint: enable=unsupported-assignment-operation

        csv_string = get_export_csv(rules, field_by_name, None)
        output = make_response(csv_string.getvalue().encode('utf-8'))
        timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
        output.headers[
            'Content-Disposition'] = f'attachment; filename=axonius-cloud_{timestamp}.csv'
        output.headers['Content-type'] = 'text/csv'
        return output
