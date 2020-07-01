import sys

from axonius.utils.debug import greenprint, yellowprint
from axonius.utils.mongo_administration import get_collection_stats
from testing.services.plugins.mongo_service import MongoService


def main():
    ms = MongoService().client
    devices_db = ms['aggregator']['devices_db']

    size_devices_db_gb = get_collection_stats(devices_db)['size'] / (1024 ** 3)
    greenprint(f'Size of devices_db before: {round(size_devices_db_gb, 2)}GB')

    # Delete nexpose warehouse rapid_installed_softwares duplicate
    print(f'Deleting rapid7_nexpose_warehouse_adapter rapid_installed_softwares')
    devices_db.update_many(
        {
            'adapters':
                {
                    '$elemMatch':
                        {
                            'plugin_name': 'rapid7_nexpose_warehouse_adapter',
                            'data.rapid_installed_softwares': {'$exists': True}
                        }
                }
        },
        {
            '$unset': {'adapters.$.data.rapid_installed_softwares': 1}
        }
    )
    size_devices_db_gb = get_collection_stats(devices_db)['size'] / (1024 ** 3)
    greenprint(f'Size of devices_db after removal: {round(size_devices_db_gb, 2)}GB')

    # Delete software name and version
    print(f'Delete installed software name-version')
    devices_db.update_many(
        {
            'adapters':
                {
                    '$elemMatch':
                        {
                            'data.installed_software.name_version': {'$exists': True}
                        }
                }
        },
        {
            '$unset': {'adapters.$.data.installed_software.$[].name_version': 1}
        }
    )
    size_devices_db_gb = get_collection_stats(devices_db)['size'] / (1024 ** 3)
    greenprint(f'Size of devices_db after removal: {round(size_devices_db_gb, 2)}GB')

    # Delete cve_description
    print(f'Delete adapters software_cves.cve_description')
    devices_db.update_many(
        {
            'adapters':
                {
                    '$elemMatch':
                        {
                            'data.software_cves.cve_description': {'$exists': True}
                        }
                }
        },
        {
            '$unset': {'adapters.$.data.software_cves.$[].cve_description': 1}
        }
    )

    size_devices_db_gb = get_collection_stats(devices_db)['size'] / (1024 ** 3)
    greenprint(f'Size of devices_db after removal: {round(size_devices_db_gb, 2)}GB')

    print(f'Delete tags (static-analysis) software_cves.cve_description')
    devices_db.update_many(
        {
            'tags':
                {
                    '$elemMatch':
                        {
                            'data.software_cves.cve_description': {'$exists': True}
                        }
                }
        },
        {
            '$unset': {'tags.$.data.software_cves.$[].cve_description': 1}
        }
    )

    size_devices_db_gb = get_collection_stats(devices_db)['size'] / (1024 ** 3)
    greenprint(f'Size of devices_db after removal: {round(size_devices_db_gb, 2)}GB')

    # Delete cve_description
    print(f'Delete adapters software_cves.cve_references')
    devices_db.update_many(
        {
            'adapters':
                {
                    '$elemMatch':
                        {
                            'data.software_cves.cve_references': {'$exists': True}
                        }
                }
        },
        {
            '$unset': {'adapters.$.data.software_cves.$[].cve_references': 1}
        }
    )

    size_devices_db_gb = get_collection_stats(devices_db)['size'] / (1024 ** 3)
    greenprint(f'Size of devices_db after removal: {round(size_devices_db_gb, 2)}GB')

    print(f'Delete tags (static-analysis) software_cves.cve_references')
    devices_db.update_many(
        {
            'tags':
                {
                    '$elemMatch':
                        {
                            'data.software_cves.cve_references': {'$exists': True}
                        }
                }
        },
        {
            '$unset': {'tags.$.data.software_cves.$[].cve_references': 1}
        }
    )

    size_devices_db_gb = get_collection_stats(devices_db)['size'] / (1024 ** 3)
    greenprint(f'Size of devices_db after removal: {round(size_devices_db_gb, 2)}GB')

    # Delete nexpose_adadapter vulns description
    print(f'Deleting nexpose adapter nexpose_vulns.description')
    devices_db.update_many(
        {
            'adapters':
                {
                    '$elemMatch':
                        {
                            'plugin_name': 'nexpose_adapter',
                            'data.nexpose_vulns.description': {'$exists': True}
                        }
                }
        },
        {
            '$unset': {'adapters.$.data.nexpose_vulns.$[].description': 1}
        }
    )
    size_devices_db_gb = get_collection_stats(devices_db)['size'] / (1024 ** 3)
    greenprint(f'Size of devices_db after removal: {round(size_devices_db_gb, 2)}GB')

    print(f'Deleting rapid7_nexpose_warehouse_adapter rapid_vulnerabilities.description')
    devices_db.update_many(
        {
            'adapters':
                {
                    '$elemMatch':
                        {
                            'plugin_name': 'rapid7_nexpose_warehouse_adapter',
                            'data.rapid_vulnerabilities.description': {'$exists': True}
                        }
                }
        },
        {
            '$unset': {'adapters.$.data.rapid_vulnerabilities.$[].description': 1}
        }
    )
    size_devices_db_gb = get_collection_stats(devices_db)['size'] / (1024 ** 3)
    greenprint(f'Size of devices_db after removal: {round(size_devices_db_gb, 2)}GB')

    yellowprint(f'Done - but there could be more devices missing in case of duplicates. Please run again')


if __name__ == '__main__':
    sys.exit(main())
