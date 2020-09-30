from typing import List, Dict, Set
import logging
from pymongo.collection import Collection

from axonius.plugin_base import PluginBase
from axonius.plugin_base import EntityType
from axonius.consts.plugin_consts import GUI_PLUGIN_NAME
from axonius.consts.gui_consts import DEVICES_DIRECT_REFERENCES_COLLECTION, USERS_DIRECT_REFERENCES_COLLECTION,\
    DEVICES_INDIRECT_REFERENCES_COLLECTION, USERS_INDIRECT_REFERENCES_COLLECTION

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=protected-access,too-many-branches


def _direct_references_collection(entity_type: EntityType):
    return PluginBase.Instance.gui_dbs.entity_saved_queries_direct[entity_type]


def _indirect_references_collection(entity_type: EntityType):
    return PluginBase.Instance.gui_dbs.entity_saved_queries_indirect[entity_type]


def _direct_references_collection_name(entity_type: EntityType):
    if entity_type == EntityType.Users:
        return DEVICES_DIRECT_REFERENCES_COLLECTION
    if entity_type == EntityType.Devices:
        return USERS_DIRECT_REFERENCES_COLLECTION
    return None


def _indirect_references_collection_name(entity_type: EntityType):
    if entity_type == EntityType.Users:
        return USERS_INDIRECT_REFERENCES_COLLECTION
    if entity_type == EntityType.Devices:
        return DEVICES_INDIRECT_REFERENCES_COLLECTION
    return None


def validate_circular_dependency(entity_type: EntityType, origin: str, targets: str):
    """
    Detect if the new references will create a circular dependency.
    :param entity_type:
    :param origin:
    :param targets:
    :return: True/False and an error.
    """
    if origin and targets:
        for target in targets:
            if origin == target:
                return False, 'Saved query cannot reference itself'

            if _indirect_references_collection(entity_type).count_documents({
                    'origin': target,
                    'target': origin
            }) > 0:
                return False, f'Error: Circular dependency detected between {origin} and {target}'
    return True, ''


def update_references(entity_type: EntityType, origin: str, targets: List[str],
                      old_targets: List[str], direct_references_col: Collection,
                      indirect_references_col: Collection):
    """
    Updating the direct reference collection after a query update.
    :param entity_type: devices/users
    :param origin
    :param targets list of targets that the origin is referencing to.
    :param old_targets list of targets that the origin no longer referencing to.
    :param direct_references_col
    :param indirect_references_col
    :param drop_collection if should drop the indirect references collection
    :return:
    """
    should_update_indirect = False

    if old_targets:
        direct_references_col.delete_many({
            'origin': origin,
            'target': {
                '$in': old_targets
            }
        })
        should_update_indirect = True

    if targets:
        docs_to_insert = []
        for target in targets:
            docs_to_insert.append({
                'origin': origin,
                'target': target
            })
        direct_references_col.insert_many(docs_to_insert)
        should_update_indirect = True

    if should_update_indirect:
        generate_indirect_references(entity_type, direct_references_col, indirect_references_col)


def update_direct_references(origin: str, targets: List[str], old_targets: List[str],
                             direct_references_col: Collection):
    """
    Updating the direct reference collection after a query update.
    :param entity_type: devices/users
    :param origin
    :param targets list of targets that the origin is referencing to.
    :param old_targets list of targets that the origin no longer referencing to.
    :param direct_references_col
    :param indirect_references_col
    :param drop_collection if should drop the indirect references collection
    :return:
    """
    if old_targets:
        direct_references_col.delete_many({
            'origin': origin,
            'target': {
                '$in': old_targets
            }
        })

    if targets:
        docs_to_insert = []
        for target in targets:
            docs_to_insert.append({
                'origin': origin,
                'target': target
            })
        direct_references_col.insert_many(docs_to_insert)


def generate_indirect_references(entity_type: EntityType, direct_references_col, indirect_references_col,
                                 drop_collection: str = True):
    """
    This method, takes the current direct references and create all the possible transitive references (indirect).
    For example, if A->B and B->C are in the direct references, we will add A->C to the list (along with A->B and B->C).
    :param entity_type:
    :param direct_references_col
    :param indirect_references_col
    :param drop_collection
    :return:
    """
    references_in_mem: Dict[str, Set[str]] = {}

    references_to_insert = []
    for reference in direct_references_col.find({}, projection={'origin': 1, 'target': 1}):
        origin = reference.get('origin')
        target = reference.get('target')
        if origin not in references_in_mem:
            references_in_mem[origin] = set()
        references_in_mem[origin].add(target)

    changed = True
    while changed:
        changed = False
        for origin in references_in_mem:  # O(n)
            targets = references_in_mem.get(origin, {})
            new_targets = set(targets)
            for target in targets:  # O(n)
                # if we have A->B, than origin is A, target is B.
                if target not in references_in_mem:
                    # if target have no references, we can't build indirect reference with it.
                    continue
                indirect_targets = references_in_mem.get(target)
                for indirect_target in indirect_targets:  # O(n)
                    if indirect_target not in targets:
                        new_targets.add(indirect_target)
                        changed = True
            references_in_mem[origin] = new_targets

    for origin in references_in_mem:
        targets = references_in_mem.get(origin)
        for target in targets:
            references_to_insert.append({
                'origin': origin,
                'target': target
            })

    if drop_collection:
        PluginBase.Instance._get_db_connection()[GUI_PLUGIN_NAME].drop_collection(
            _indirect_references_collection_name(entity_type))
    if references_to_insert:
        indirect_references_col.insert_many(references_to_insert)
