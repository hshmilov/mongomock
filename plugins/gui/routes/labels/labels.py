from flask import (jsonify)

from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
from gui.routes.labels.labels_catalog import LABELS_CATALOG

# pylint: disable=no-self-use


@gui_category_add_rules('labels')
class Labels:
    @gui_route_logged_in(enforce_permissions=False)
    def get_labels(self):
        return jsonify(LABELS_CATALOG)
