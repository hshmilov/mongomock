import logging
# pylint: disable=import-error
from tenable.io import TenableIO


logger = logging.getLogger(f'axonius.{__name__}')


def get_export_asset_plus_vulns(access_key, secret_key, proxies):
    try:
        tio = TenableIO(access_key, secret_key, proxies=proxies,
                        vendor='Axonius', product='Axonius', build='1.0.0')
        assets = tio.exports.assets()
        assets_list_dict = dict()
        for asset in assets:
            try:
                asset_id = asset.get('id')
                if not asset_id:
                    logger.warning(f'Got asset with no id. Asset raw data: {asset}')
                    continue
                assets_list_dict[asset_id] = asset
                assets_list_dict[asset_id]['vulns_info'] = []
            except Exception:
                logger.exception(f'Problem with asset {asset}')
    except Exception as e:
        logger.exception(f'exception in getting export')
        return str(e)
    try:
        vulns_list = tio.exports.vulns()
    except Exception:
        vulns_list = []
        logger.exception('General error while getting vulnerabilities')
    try:
        for vuln_raw in vulns_list:
            try:
                # Trying to find the correct asset for all vulnerability line in the array
                asset_id_for_vuln = (vuln_raw.get('asset') or {}).get('uuid')
                if not asset_id_for_vuln:
                    logger.warning(f'No id for vuln {vuln_raw}')
                    continue
                assets_list_dict[asset_id_for_vuln]['vulns_info'].append(vuln_raw)
            except Exception:
                logger.debug(f'Problem with vuln raw {vuln_raw}')
    except Exception:
        logger.exception('General error while getting vulnerabilities fetch')
    yield from assets_list_dict.items()
    return None
