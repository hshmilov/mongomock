import logging
import json

from datetime import datetime
from bson import ObjectId

from axonius.consts.gui_consts import USER_NAME, ROLE_ID
from axonius.consts.plugin_consts import (PREDEFINED_USER_NAMES)
from axonius.plugin_base import return_error
from axonius.utils.permissions_helper import PermissionCategory
from gui.logic.filter_utils import filter_archived
from gui.logic.routing_helper import gui_section_add_rules, gui_route_logged_in
# pylint: disable=no-member


logger = logging.getLogger(f'axonius.{__name__}')


@gui_section_add_rules('users/bulk', permission_section=PermissionCategory.Users)
class UserBulk:
    @gui_route_logged_in(methods=['DELETE'], activity_params=['count'])
    def delete_users_bulk(self):
        """
        archive all users or all users with id found in a given set.
        :return:
        status code 200 - archived all requested users and invalidate their session
        status code 202 - the request partially succeed. Not akk users archived
        status code 400 - server error. Operation failed.
        """
        users_collection = self._users_collection
        request_data = self.get_request_data_as_object()
        ids = request_data.get('ids', [])
        include = request_data.get('include', True)

        # if include is equal to False, all users should be deleted beside admin, _axonius & _axonius_ro
        if not include:
            logger.info('Update users with include = False')
            result = users_collection.update_many(filter_archived({
                USER_NAME: {'$nin': PREDEFINED_USER_NAMES},
                '_id': {'$nin': [ObjectId(user_id) for user_id in ids]}
            }), {
                '$set': {'archived': True}
            })

            # handle response
            if result.modified_count < 1:
                err_msg = 'operation failed, could not delete users\''
                logger.info(err_msg)
                return return_error(err_msg, 400)

            response_str = json.dumps({
                'count': str(result.modified_count)
            })
            if result.matched_count != result.modified_count:
                logger.info(f'Deleted {result.modified_count} out of {result.matched_count} users')
                return response_str, 202

            logger.info(f'Bulk deletion users succeeded')
            return response_str, 200

        partial_success = False
        deletion_success = False
        deletion_count = 0
        for user_id in ids:
            existed_user = users_collection.find_one_and_update(filter_archived({
                '_id': ObjectId(user_id)
            }), {
                '$set': {'archived': True}
            }, projection={
                USER_NAME: 1
            })

            if existed_user is None:
                logger.info(f'User with id {user_id} does not exists')
                partial_success = True
            else:
                deletion_count += 1
            deletion_success = True
            self._invalidate_sessions([user_id])
            name = existed_user[USER_NAME]
            logger.info(f'Users {name} with id {user_id} has been archive')

        # handle response
        if not deletion_success:
            err_msg = 'operation failed, could not delete users\''
            logger.info(err_msg)
            return return_error(err_msg, 400)
        response_str = json.dumps({
            'count': str(deletion_count)
        })
        if deletion_success and partial_success:
            logger.info('Deletion partially succeeded')
            return response_str, 202
        logger.info(f'Bulk deletion users succeeded')
        return response_str, 200

    @gui_route_logged_in('assign_role', methods=['POST'], activity_params=['name', 'count'])
    def users_assign_role_bulk(self):
        """
        set new role_id to all users or all users with id found in a given set.
        :return:
        status code 200 - updated all requested users
        status code 202 - the request partially succeed. Not akk users archived
        status code 400 - invalid request. role_id not supplied
        status code 500 - server error. Operation failed.
        """
        users_collection = self._users_collection
        request_data = self.get_request_data_as_object()
        ids = request_data.get('ids', [])
        include = request_data.get('include', True)
        role_id = request_data.get(ROLE_ID)

        # axonius roles is not assignable
        axonius_roles_ids = self._get_axonius_roles_ids()
        if ObjectId(role_id) in axonius_roles_ids:
            logger.info('Attempt to assign axonius role to users')
            return return_error('role is not assignable', 400)

        if not role_id:
            return return_error('role id is required', 400)

        # if include value is False, all users should be updated (beside admin, _axonius and _axonius_ro)
        if not include:
            find_query = filter_archived({
                '_id': {'$nin': [ObjectId(user_id) for user_id in ids]},
                USER_NAME: {'$nin': PREDEFINED_USER_NAMES},
            })
        else:
            find_query = filter_archived({
                '_id': {'$in': [ObjectId(user_id) for user_id in ids]},
                USER_NAME: {'$nin': PREDEFINED_USER_NAMES},
            })

        result = users_collection.update_many(find_query, {
            '$set': {ROLE_ID: ObjectId(role_id), 'last_updated': datetime.now()}
        })

        if result.modified_count < 1:
            logger.info('operation failed, could not update users\' role')
            return return_error('operation failed, could not update users\' role', 400)
        user_ids = [str(user_id.get('_id')) for user_id in users_collection.find(find_query, {'_id': 1})]
        self._invalidate_sessions(user_ids)
        response_str = json.dumps({
            'count': str(result.modified_count),
            'name': self._roles_collection.find_one({'_id': ObjectId(role_id)}, {'name': 1}).get('name', '')
        })
        if result.matched_count != result.modified_count:
            logger.info(f'Bulk assign role modified {result.modified_count} out of {result.matched_count}')
            return response_str, 202

        logger.info(f'Bulk assign role modified succeeded')
        return response_str, 200
