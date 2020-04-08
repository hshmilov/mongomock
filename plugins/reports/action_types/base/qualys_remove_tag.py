import contextlib
import functools
import logging

from typing import Set, Dict

from axonius.clients.qualys import consts
from axonius.clients.qualys.connection import QualysScansConnection
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from reports.action_types.action_type_base import ActionTypeBase, generic_fail, generic_success
from reports.action_types.base.qualys_utils import QualysActionUtils, ACTION_CONFIG_TAGS
#pylint: disable=too-many-locals

logger = logging.getLogger(f'axonius.{__name__}')


class QualysRemoveTag(ActionTypeBase):
    @staticmethod
    def config_schema() -> dict:
        return QualysActionUtils.GENERAL_CONFIG_SCHEMA

    @staticmethod
    def default_config() -> dict:
        default_config = QualysActionUtils.GENERAL_DEFAULT_CONFIG.copy()
        return default_config

    def _run(self) -> EntitiesResult:
        try:

            requested_tags_set = set(self._config.get(ACTION_CONFIG_TAGS) or [])
            logger.info(f'Running Remove Qualys Tag From HostAsset Tag action with tags {requested_tags_set}')

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

                # retrieve the requested tag ids and validate their existence
                tag_ids_by_name = connection.list_tag_ids_by_name()
                existing_requested_tag_id_by_name = {tag_name: tag_ids_by_name[tag_name] for tag_name in
                                                     requested_tags_set
                                                     if tag_name in tag_ids_by_name}
                missing_tags = set(requested_tags_set) - set(existing_requested_tag_id_by_name.keys())
                if missing_tags:
                    logger.info(f'Failed to locate requested tags: {missing_tags}/{requested_tags_set}')
                    return (yield from generic_fail(axon_by_qualys_id.values(),
                                                    f'Missing tags: {",".join(missing_tags)}'))

                # add tags to hosts and push a revert tags restore operation
                host_ids = axon_by_qualys_id.keys()
                requested_tag_ids = set(existing_requested_tag_id_by_name.values())
                preoperation_tags_by_host = dict(connection.iter_tags_by_host_id(host_ids))
                _ = connection.remove_host_tags(host_ids, requested_tag_ids)
                for host_id in host_ids:
                    # we push separate revert operation per host due to their potential different state
                    preop_tag_dicts = preoperation_tags_by_host.get(host_id)
                    if not preop_tag_dicts:
                        logger.debug(f'failed to locate host {host_id} in existing tags, ditching revert operation.')
                        continue
                    # compute revertible tags for addition - any requested tag that existed beforehand.
                    revertible_tags = requested_tag_ids.intersection({tag_dict['id'] for tag_dict in preop_tag_dicts})
                    if revertible_tags:
                        logger.debug(f'Appending revert tag addition operation for host {host_id}'
                                     f' for revertible tags {revertible_tags}')
                        # pylint: disable=no-member
                        revert_stack.callback(functools.partial(connection.add_host_existing_tags,
                                                                [host_id], revertible_tags))

                # re-list tags to make sure they were added
                excessive_tag_names_by_host_id = {
                    host_id: requested_tags_set.intersection({tag_dict['name'] for tag_dict in tags_dicts})
                    for host_id, tags_dicts in connection.iter_tags_by_host_id(host_ids)
                }  # type: Dict[str, Set[str]]
                logger.debug(f'Excessive tags by host: {excessive_tag_names_by_host_id}')

                # if any of the hosts has an excessive tag, fail everything
                if any((len(excessive_tags) > 0) for excessive_tags in excessive_tag_names_by_host_id.values()):
                    for host_id, excessive_tags in excessive_tag_names_by_host_id.items():
                        logger.debug(f'host {host_id} still has excessive tags {excessive_tags}')

                        axon_id = axon_by_qualys_id.get(host_id)
                        if not axon_id:
                            logger.warning(f'Retrieved unintentional host {host_id}, ditching it.')
                            continue

                        error_msg = f'Failed due to excessive tags in other device'
                        if excessive_tags:
                            error_msg = f'Failed due to excessive tags: {",".join(excessive_tags)}'

                        yield EntityResult(axon_id, False, error_msg)
                    return None
                    # Note - Revert happens here in LIFO order #

                # everything went well - cancel revert stack
                logger.info('Operation Succeeded')
                # pylint: disable=no-member
                _ = revert_stack.pop_all()

            return (yield from generic_success(axon_by_qualys_id.values()))
        except Exception:
            logger.exception(f'Problem with action remove tag')
            return (yield from generic_fail(self._internal_axon_ids, 'Unexpected error during action'))
