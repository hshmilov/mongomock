import logging
from typing import Tuple

from axonius.plugin_base import EntityType, PluginBase
from axonius.utils.mongo_administration import get_collection_stats

logger = logging.getLogger(f'axonius.{__name__}')


def kb_to_gb(value):
    return round(value / (1024 ** 2), 2)


# pylint: disable=W0212
def calculate_snapshot(total_data_disk_space_in_kb: int,
                       free_data_disk_space_in_kb: int,
                       retention_days_configured: int) -> Tuple[int, int, int]:
    """
    Calculating -
        1. the latest snapshot size (using historical_year_month_day collection)
        2. the the maximum possible snapshots with the current disk size (assuming the current db as the snapshot
        size)
        3. the number of days left for snapshots (for the free space left).
    :param total_data_disk_space_in_kb: total size of disk taken from node metrics.
    :param free_data_disk_space_in_kb: free disk space taken from node metrics.
    :param retention_days_configured: account's retention days configured.
    :return:
    """
    logger.info('Starting snapshot calculation...')
    max_snapshot_days = None
    snapshot_days_left = None
    last_snapshot_size = None

    if not total_data_disk_space_in_kb:
        return max_snapshot_days, snapshot_days_left, last_snapshot_size

    total_size_of_cycle_in_bytes = 0

    try:
        # 1. Getting the latest snapshot size available for devices and users.
        last_snapshot_size_in_kb = calculate_last_snapshot_size()

        # 2. calculating "next" snapshot size, and assuming this size for days calculations.
        for entity_type in EntityType:
            col = PluginBase.Instance._entity_db_map[entity_type]
            if col:
                storage_stats = get_collection_stats(col)
                storage = storage_stats['storageSize']
                indexes = storage_stats['totalIndexSize']
                total_size_of_cycle_in_bytes += storage + indexes

        total_size_of_cycle_in_kb = total_size_of_cycle_in_bytes / 1024

        max_snapshot_days = calculate_retention_days(total_data_disk_space_in_kb, total_size_of_cycle_in_kb)
        snapshot_days_left = calculate_retention_days(free_data_disk_space_in_kb, total_size_of_cycle_in_kb)

        if retention_days_configured and retention_days_configured > max_snapshot_days:
            snapshot_days_left = None
        return max_snapshot_days, snapshot_days_left, last_snapshot_size_in_kb
    except Exception as e:
        logger.exception(e)
        return None, None, None


def calculate_last_snapshot_size():
    device_storage_size = 0
    users_storage_size = 0
    users_indexes_size = 0
    devices_indexes_size = 0

    collections_devices = PluginBase.Instance.aggregator_db_connection.list_collection_names(
        filter={'name': {'$regex': r'historical_devices_\d{4}_\d{2}_\d{2}'}})
    if collections_devices and len(collections_devices) > 0:
        collections_devices.sort()
        latest_devices_snapshot_collection = PluginBase.Instance.aggregator_db_connection[list(collections_devices)[-1]]
        storage_stats = get_collection_stats(latest_devices_snapshot_collection)
        device_storage_size = storage_stats['storageSize']
        devices_indexes_size = storage_stats['totalIndexSize']

    collections_users = PluginBase.Instance.aggregator_db_connection.list_collection_names(
        filter={'name': {'$regex': r'historical_users_\d{4}_\d{2}_\d{2}'}})
    if collections_users and len(collections_users) > 0:
        collections_users.sort()
        latest_users_snapshot_collection = PluginBase.Instance.aggregator_db_connection[list(collections_users)[-1]]
        storage_stats = get_collection_stats(latest_users_snapshot_collection)
        users_storage_size = storage_stats['storageSize']
        users_indexes_size = storage_stats['totalIndexSize']

    total_size_in_bytes = (device_storage_size + devices_indexes_size) + (users_storage_size + users_indexes_size)

    return round(total_size_in_bytes / 1024)


def calculate_retention_days(total_free_space_in_kb, total_size_of_cycle_in_kb):
    total_free_disk_space_in_mb = total_free_space_in_kb / 1024  # kb_to_gb(total_free_space)
    total_space_needed_for_cycle_in_mb = max(round((total_size_of_cycle_in_kb / 1024), 2),
                                             1)  # Defaulting to 1mb.
    # 30 days, each day we have once in history and one in cache.
    min_size_for_30_days = round(total_space_needed_for_cycle_in_mb * (30 + 30), 2)

    max_snapshot_days = 0
    if total_free_disk_space_in_mb > min_size_for_30_days:
        max_snapshot_days_after_30_days = round((total_free_disk_space_in_mb - min_size_for_30_days)
                                                / total_space_needed_for_cycle_in_mb)
        max_snapshot_days = 30 + max_snapshot_days_after_30_days
    else:
        # No space for 30 days of cache.
        next_cycle_size = total_space_needed_for_cycle_in_mb + 2 * total_space_needed_for_cycle_in_mb
        while next_cycle_size < total_free_disk_space_in_mb:
            next_cycle_size += 2 * total_space_needed_for_cycle_in_mb
            max_snapshot_days += 1

    return max_snapshot_days
