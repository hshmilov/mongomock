import contextlib
import functools
import logging

from typing import Set, Dict

from axonius.clients.qualys import consts
from axonius.clients.qualys.connection import QualysScansConnection
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from reports.action_types.action_type_base import ActionTypeBase, generic_fail, generic_success
from reports.action_types.base.qualys_utils import QualysActionUtils, ACTION_CONFIG_TAGS

logger = logging.getLogger(f'axonius.{__name__}')

ACTION_CONFIG_PARENT_TAG = 'parent_tag'


class QualysAddTag(ActionTypeBase):
    @staticmethod
    def config_schema() -> dict:
        schema = QualysActionUtils.GENERAL_CONFIG_SCHEMA.copy()
        schema['items'].append({'name': ACTION_CONFIG_PARENT_TAG, 'title': 'Parent tag name', 'type': 'string'})
        return schema

    @staticmethod
    def default_config() -> dict:
        default_config = QualysActionUtils.GENERAL_DEFAULT_CONFIG.copy()
        default_config[ACTION_CONFIG_PARENT_TAG] = None
        return default_config

    # pylint: disable=too-many-locals,too-many-statements
    def _run(self) -> EntitiesResult:
        try:

            parent_tag_name = self._config.get(ACTION_CONFIG_PARENT_TAG)
            requested_tags_set = set(self._config.get(ACTION_CONFIG_TAGS) or [])
            logger.info(f'Running Add Qualys HostAsset Tag action with tags {requested_tags_set}'
                        f' and parent {parent_tag_name}')

            # pylint: disable=protected-access
            connection = QualysScansConnection(domain=self._config[consts.QUALYS_SCANS_DOMAIN],
                                               verify_ssl=self._config[consts.VERIFY_SSL],
                                               username=self._config.get(consts.USERNAME),
                                               password=self._config.get(consts.PASSWORD),
                                               https_proxy=self._config.get(consts.HTTPS_PROXY))

            current_result = self._get_entities_from_view({
                'internal_axon_id': 1,
                'adapters.plugin_name': 1,
                'adapters.data.qualys_id': 1,
            })

            # Filter out invalid devices returned by the query
            axon_by_qualys_id = (yield from QualysActionUtils.get_axon_by_qualys_id_and_reject_invalid(current_result))

            with connection, contextlib.ExitStack() as revert_stack:  # type: contextlib.ExitStack

                tag_ids_by_name = connection.list_tag_ids_by_name()
                logger.debug(f'Located tags: {tag_ids_by_name}')
                if not tag_ids_by_name:
                    message = 'Failed retrieving existing tags'
                    logger.error(message)
                    return (yield from generic_fail(axon_by_qualys_id.values(), message))

                # create missing tags
                created_tag_ids = set()  # type: Set[str]
                tag_names_to_create = requested_tags_set - set(tag_ids_by_name.keys())
                if tag_names_to_create:

                    # if parent given and doesnt exist - fail all devices
                    if parent_tag_name and parent_tag_name not in tag_ids_by_name:
                        message = f'Failed locating parent tag "{parent_tag_name}"'
                        logger.error(message)
                        return (yield from generic_fail(axon_by_qualys_id.values(), message))

                    # create the tags and push a revert removal operation
                    parent_tag_id = tag_ids_by_name.get(parent_tag_name)
                    created_tag_ids_by_name, failed_tag_name = connection.create_tags(tag_names_to_create,
                                                                                      parent_tag_id=parent_tag_id)
                    # Note - delete_tags would also remove the tags from any
                    #        hostasset they've been successfully assigned to
                    # pylint: disable=no-member
                    revert_stack.callback(functools.partial(connection.delete_tags, created_tag_ids_by_name.values()))
                    if failed_tag_name:
                        logger.error(f'The following tag failed to create: {failed_tag_name}')
                        return (yield from generic_fail(axon_by_qualys_id.values(),
                                                        f'Failed Creating tag "{failed_tag_name}"'))
                    tag_ids_by_name.update(created_tag_ids_by_name)
                    created_tag_ids.update(created_tag_ids_by_name.values())

                # add tags to hosts and push a revert tags restore operation
                host_ids = axon_by_qualys_id.keys()
                preoperation_tags_by_host = dict(connection.iter_tags_by_host_id(host_ids))
                requested_tag_ids = {tag_ids_by_name[tag_name] for tag_name in requested_tags_set}
                _ = connection.add_host_existing_tags(host_ids, requested_tag_ids)
                for host_id in host_ids:
                    # we push separate revert operation per host due to their potential different state
                    preop_tag_dicts = preoperation_tags_by_host.get(host_id)
                    if not preop_tag_dicts:
                        logger.debug(f'failed to locate host {host_id} in existing tags, ditching revert operation.')
                        continue
                    # compute revertible tags for removal - any requested tag that wasn't created and didn't pre-exist.
                    revertible_tags = (requested_tag_ids - created_tag_ids
                                       - {tag_dict['id'] for tag_dict in preop_tag_dicts})
                    if revertible_tags:
                        logger.debug(f'Appending revert tag removal operation for host {host_id}'
                                     f' for revertible tags {revertible_tags}')
                        # pylint: disable=no-member
                        revert_stack.callback(functools.partial(connection.remove_host_tags,
                                                                [host_id], revertible_tags))

                # re-list tags to make sure they were added
                missing_tag_names_by_host_id = {
                    host_id: (requested_tags_set - {tag_dict['name'] for tag_dict in tags_dicts})
                    for host_id, tags_dicts in connection.iter_tags_by_host_id(host_ids)
                }  # type: Dict[str, Set[str]]
                logger.debug(f'Missing tags by host: {missing_tag_names_by_host_id}')

                # if any of the hosts has a missing tag, fail everything
                if any((len(missing_tags) > 0) for missing_tags in missing_tag_names_by_host_id.values()):
                    for host_id, missing_tags in missing_tag_names_by_host_id.items():
                        logger.debug(f'host {host_id} missing tags {missing_tags}')

                        axon_id = axon_by_qualys_id.get(host_id)
                        if not axon_id:
                            logger.warning(f'Retrieved unintentional host {host_id}, ditching it.')
                            continue

                        error_msg = f'Failed due to missing tags in other device'
                        if missing_tags:
                            error_msg = f'Failed due to missing tags: {",".join(missing_tags)}'

                        yield EntityResult(axon_id, False, error_msg)
                    return None
                    # Note - Revert happens here in LIFO order #

                # everything went well - cancel revert stack
                logger.info('Operation Succeeded, flushing revert stack')
                # pylint: disable=no-member
                _ = revert_stack.pop_all()

            return (yield from generic_success(axon_by_qualys_id.values()))
        except Exception:
            logger.exception(f'Problem with action add tag')
            return (yield from generic_fail(self._internal_axon_ids, 'Unexpected error during action'))
