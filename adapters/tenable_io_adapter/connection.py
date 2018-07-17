from axonius.clients.rest.connection import RESTConnection
from tenable_io_adapter import consts
import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.clients.rest.exception import RESTException
import time


class TenableIoConnection(RESTConnection):

    def __init__(self, *args, access_key: str = "",  secret_key: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._access_key = access_key
        self._secret_key = secret_key
        if self._username is not None and self._username != "" and self._password is not None and self._password != "":
            # We should use the user and password
            self._should_use_token = True
        elif self._access_key is not None and self._access_key != "" and \
                self._secret_key is not None and self._secret_key != "":
            # We should just use the given api keys
            self._should_use_token = False
            self._set_api_headers()
        else:
            raise RESTException("Missing user/password or api keys")

    def _set_token_headers(self, token):
        """ Sets the API token, in the appropriate header, for valid requests

        :param str token: API Token
        """
        self._token = token
        self._session_headers['X-Cookie'] = 'token={0}'.format(token)

    def _set_api_headers(self):
        """ Setting headers to include the given api key
        """
        self._permanent_headers['X-ApiKeys'] = f'accessKey={self._access_key}; secretKey={self._secret_key}'

    def _connect(self):
        if self._should_use_token is True:
            response = self._post('session', body_params={'username': self._username, 'password': self._password})
            if 'token' not in response:
                error = response.get('errorCode', 'Unknown connection error')
                message = response.get('errorMessage', '')
                if message:
                    error = '{0}: {1}'.format(error, message)
                raise RESTException(error)
            self._set_token_headers(response['token'])
        else:
            self._get('scans')

    def _get_export_data(self, export_type):
        export_uuid = self._post(f"{export_type}/export",
                                 body_params={"chunk_size": consts.DEVICES_PER_PAGE})["export_uuid"]
        available_chunks = set()
        response = self._get(f"{export_type}/export/{export_uuid}/status")
        available_chunks.update(response.get("chunks_available", []))
        number_of_sleeps = 0
        while response.get("status") != "FINISHED" and number_of_sleeps < consts.NUMBER_OF_SLEEPS:
            try:
                response = self._get(f"{export_type}/export/{export_uuid}/status")
                available_chunks.update(response.get("chunks_available"))
            except Exception:
                logger.exception(f"Problem with getting chunks for {export_uuid}")
            time.sleep(consts.TIME_TO_SLEEP)
            number_of_sleeps += 1
        export_list = []
        for chunk_id in available_chunks:
            try:
                export_list.extend(self._get(f"{export_type}/export/{export_uuid}/chunks/{chunk_id}"))
            except Exception:
                logger.exception(f"Problem in getting specific chunk {chunk_id} from {export_uuid} type {export_type}")
        return export_list

    def get_device_list(self):
        assets_list = self._get_export_data("assets")
        assets_list_dict = dict()
        # Creating dict out of assets_list
        for asset in assets_list:
            try:
                asset_id = asset.get("id", "")
                if asset_id is None or asset_id == "":
                    logger.warning(f"Got asset with no id. Asset raw data: {asset}")
                    continue
                assets_list_dict[asset_id] = asset
                assets_list_dict[asset_id]["vulns_info"] = []
            except Exception:
                logger.exception(f"Problem with asset {asset}")
        try:
            vulns_list = self._get_export_data("vulns")
        except Exception:
            vulns_list = []
            logger.exception("General error while getting vulnerabilities")
        for vuln_raw in vulns_list:
            try:
                # Trying to find the correct asset for all vulnerability line in the array
                asset_id_for_vuln = vuln_raw.get("asset", {}).get("uuid", "")
                if asset_id_for_vuln is None or asset_id_for_vuln == "":
                    logger.warning(f"No id for vuln {vuln_raw}")
                    continue
                assets_list_dict[asset_id_for_vuln]["vulns_info"].append(vuln_raw)
            except Exception:
                logger.exception(f"Problem with vuln raw {vuln_raw}")
        yield from assets_list_dict.values()
