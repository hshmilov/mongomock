import logging
from typing import List

import googleapiclient.discovery
from google.oauth2 import service_account

logger = logging.getLogger(f'axonius.{__name__}')

DEVICES_PER_PAGE = 100
MAX_NUMBER_OF_DEVICES = 1000000


class GSuiteAdminConnection:
    def __init__(self, auth_json: dict, account_to_impersonate: str, scopes: List[str]):
        """
        Creates a new connection to https://developers.google.com/admin-sdk/
        :param auth_json: The auth JSON - https://developers.google.com/identity/protocols/OAuth2ServiceAccount
        :param account_to_impersonate: An admin account to impersonate
        :param scopes: list of scopes needed for actions
        """
        credentials = service_account.Credentials.from_service_account_info(auth_json, scopes=scopes)
        delegated_credentials = credentials.with_subject(account_to_impersonate)
        # this line is copied directly from https://developers.google.com/admin-sdk/directory/v1/quickstart/python
        # this build the service 'admin' in the version 'directory_v1', i.e.
        # accessing apis that look like:
        # https://www.googleapis.com/admin/directory/v1/...
        self._connection = googleapiclient.discovery.build('admin', 'directory_v1', credentials=delegated_credentials)

    def get_mobile_devices(self) -> List[dict]:
        """
        Get mobile devices
        """
        # The mobile API is like this, https://developers.google.com/admin-sdk/directory/v1/guides/manage-mobile-devices
        mobile_devices = self._connection.mobiledevices().list(customerId='my_customer',
                                                               maxResults=DEVICES_PER_PAGE).execute()
        yield from mobile_devices.get('mobiledevices', [])
        next_page_token = mobile_devices.get('nextPageToken') or ''
        number_of_pages = 1
        while next_page_token and (number_of_pages * DEVICES_PER_PAGE < MAX_NUMBER_OF_DEVICES):
            try:
                number_of_pages += 1
                mobile_devices = self._connection.mobiledevices().list(customerId='my_customer',
                                                                       pageToken=next_page_token,
                                                                       maxResults=DEVICES_PER_PAGE).execute()
                yield from mobile_devices.get('mobiledevices', [])
                next_page_token = mobile_devices.get('nextPageToken') or ''
            except Exception:
                # Breaking here to Avoid infinite loop
                logger.exception(f'Problem getting page number {number_of_pages}')
                break

    def get_users(self) -> List[dict]:
        """
        Get users
        """
        users = self._connection.users().list(customer='my_customer', maxResults=DEVICES_PER_PAGE).execute()

        yield from users.get('users', [])
        next_page_token = users.get('nextPageToken') or ''
        number_of_pages = 1
        while next_page_token and (number_of_pages * DEVICES_PER_PAGE < MAX_NUMBER_OF_DEVICES):
            try:
                number_of_pages += 1
                users = self._connection.users().list(customer='my_customer',
                                                      pageToken=next_page_token,
                                                      maxResults=DEVICES_PER_PAGE).execute()
                yield from users.get('users', [])
                next_page_token = users.get('nextPageToken') or ''
            except Exception:
                # Breaking here to Avoid infinite loop
                logger.exception(f'Problem getting page number {number_of_pages}')
                break

    def get_user_groups(self, userKey: str) -> List[dict]:
        """
        Get all groups that a user is in
        :param userKey: The ID of the user to query
        """
        return self._connection.groups().list(userKey=userKey).execute().get('groups', [])
