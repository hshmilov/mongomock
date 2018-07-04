import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from tenable_security_center_adapter import consts


class TenableSecurityScannerConnection(RESTConnection):
    # This code heavily relies on pyTenable https://github.com/tenable/pyTenable/blob/
    # 24e0fbd6191907b46c4e2e1b6cee176e93ad6d4d/tenable/securitycenter/securitycenter.py
    def _connect(self):
        if self._username is not None and self._password is not None:
            # Based on Tenable SCCV Documentation (https://docs.tenable.com/sccv/api/index.html)
            # and https://docs.tenable.com/sccv/api/Token.html
            # We need to post to 'token' and get the token and cookie.
            connection_dict = {'username': self._username,
                               'password': self._password,
                               'releaseSession': True}  # releaseSession is default false

            response = self._post("token", body_params=connection_dict)
            if response.get('releaseSession') is True:
                raise RESTException(f"User {self._username} has reached its maximum login limit.")

            # We don't have to set the cookie since RESTConnection does that for us (uses request.Session)
            self._session_headers["X-SecurityCenter"] = str(response['token'])
        else:
            raise RESTException("No user name or password")

    def _do_request(self, *args, **kwargs):
        resp = super()._do_request(*args, **kwargs)

        try:
            if str(resp["error_code"]) != "0":
                raise RESTException(f"API Error {resp['error_code']}: {resp['error_msg']}")
        except KeyError:
            pass

        return resp['response']

    def close(self):
        # Deletes the token associated with the logged in User (https://docs.tenable.com/sccv/api/Token.html)
        try:
            self._delete("token")
        except Exception:
            logger.exception("Couldn't delete token")
        super().close()

    def get_device_list(self):
        repositories = self._get('repository')
        repositories_ids = [repository.get('id', '') for repository in repositories]
        for repository_id in repositories_ids:
            try:
                if repository_id != '':
                    yield from self.get_device_list_from_repository(repository_id)
            except Exception:
                logger.exception(f"Problem with repository {repository_id}")

    def get_device_list_from_repository(self, repository_id):
        start_offest = 0
        end_offset = consts.DEVICE_PER_PAGE
        # This API is half documented. Ofri got this API after playing with the instance
        response = self._post("analysis", body_params={"type": "vuln",
                                                       "sourceType": "cumulative",
                                                       "query": {'tool': 'sumip',
                                                                 'type': 'vuln',
                                                                 'startOffset': start_offest,
                                                                 'endOffset': end_offset,
                                                                 'filters': [{
                                                                     'filterName': 'repository', 'id': 'repository',
                                                                     'isPredefined': True, 'operator': '=',
                                                                     'type': 'vuln', 'value': [{'id': repository_id}]
                                                                 }]}})
        start_offest += consts.DEVICE_PER_PAGE
        end_offset += consts.DEVICE_PER_PAGE
        yield from response["results"]
        total_records = response["totalRecords"]
        records_returned = response["returnedRecords"]
        logger.info(f"Got {records_returned} out of {total_records} at the first page")
        while int(start_offest) < int(total_records) \
                and int(start_offest) < int(consts.MAX_RECORDS):
            try:
                response = self._post("analysis", body_params={"type": "vuln",
                                                               "sourceType": "cumulative",
                                                               "query": {'tool': 'sumip',
                                                                         'type': 'vuln',
                                                                         'startOffset': start_offest,
                                                                         'endOffset': end_offset}})
                yield from response["results"]
                records_returned = response["returnedRecords"]
                logger.info(f"Got {records_returned} out of {total_records} at offset {start_offest}")
            except Exception:
                logger.exception(f"Problems at offset {start_offest}")
            start_offest += consts.DEVICE_PER_PAGE
            end_offset += consts.DEVICE_PER_PAGE

    def get_data_about_list_of_ips(self, ips):
        """
        Allows us to get data about a list of ip's.
        :param ips: a list of strings, each one is an ip.
        :return:
        """
        # We have two approaches here. The first one is to get a list of repositories, then go through
        # their ip subnet, and try to query information for each of these subnets.
        # Since we have no option to get a list of the scanned ip's the only option is to go through the subnet.
        #
        # But this is a bad idea which can issue a HUGE number of get requests and take a lot of time.
        # This is why we prefer to get a list of ip's and return info about them.
        # Since NSC is a scanner anyway then we can allow ourselves to bring data only on hosts
        # that we already know of.
        #
        # Some ip's that we get are local and irrelevant. We will bring all repositories, and check if the ip
        # checked is at least a member of one of them. only in this case we will query.

        """
        # Do not rescure getting all subnets right now because we have no adapter to check it with.
        reps = self._get("repository", url_params={"fields": "ipRange"})
        """
        for ip in ips:
            try:
                # Note that if this ip is listed in numerous repositories, we get info only about the first
                # repository.
                # https://docs.tenable.com/sccv/api/IP-Information.html

                resp = self._get("ipInfo", url_params={
                    "fields": ",".join(IP_INFO_FIELDS),
                    "ip": ip})

                yield resp
            except RESTException:
                logger.exception(f"Exception getting data about ip {ip}. Continuing")


# All fields are taken from https://docs.tenable.com/sccv/api/IP-Information.html
# unimportant data is commented.
IP_INFO_FIELDS = [
    "ip",   # This is a must field by the documentation but we still put it
    "repositoryID",  # This is a must field by the documentation but we still put it
    "repositories",
    "repository",
    "score",
    "total",
    "severityInfo",
    "severityLow",
    "severityMedium",
    "severityHigh",
    "severityCritical",
    "macAddress",
    "policyName",
    # "pluginSet",
    "netbiosName",
    "dnsName",
    # "osCPE",
    # "biosGUID",
    # "tpmID",
    "mcafeeGUID",
    "lastAuthRun",
    "lastUnauthRun",
    # "severityAll",
    "os",
    "hasPassive",
    "hasCompliance",
    "lastScan",
    # "links"
]
