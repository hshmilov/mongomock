from flask import jsonify

from axonius.consts.gui_consts import RootMasterNames
from axonius.plugin_base import return_error
from axonius.utils.root_master.root_master import restore_from_s3_key
from gui.logic.routing_helper import gui_section_add_rules, gui_route_logged_in

# pylint: disable=no-member


@gui_section_add_rules('central_core')
class CentralCore:
    @gui_route_logged_in()
    def central_core_get(self):
        """Get the current central core (root master) settings from feature flags.

        jim: 3.3: added for esentire/cimpress automation

        path: /api/settings/central_core

        :return: dict
        """
        return self._get_central_core_settings()

    @gui_route_logged_in(methods=['POST'])
    def central_core_update(self):
        """Update the current central core (root master) settings from feature flags.

        jim: 3.3: added for esentire/cimpress automation

        path: /api/settings/central_core

        :return: dict
        """
        return self._update_central_core_settings()

    @gui_route_logged_in(
        rule='restore',
        methods=['POST']
    )
    def central_core_restore(self):
        """Start the restore process.

        jim: 3.3: added for esentire/cimpress automation

        restore_type: str, required
            type of restore to perform

        path: /api/settings/central_core

        :return: dict
        """
        request_data = self.get_request_data_as_object()
        restore_type = request_data.get('restore_type')
        restore_types = {'aws': self.central_core_restore_aws}

        if restore_type not in restore_types:
            restore_types = ', '.join(list(restore_types))
            err = f'Invalid restore_type={restore_type!r}, must be one of: {restore_types}'
            return return_error(error_message=err, http_status=400, additional_data=None)

        restore_method = restore_types[restore_type]
        return restore_method(request_data=request_data)

    def central_core_restore_aws(self, request_data):
        """Perform a restore from an AWS S3.

        jim: 3.3: added for esentire/cimpress automation

        :return: dict
        """
        explain = {
            'key_name': {
                'type': 'str',
                'required': True,
                'description': 'Name of file in [bucket_name] to restore',
                'default': None,
            },
            'bucket_name': {
                'type': 'str',
                'required': False,
                'description': 'Name of bucket in S3 to get [key_name] from',
                'default': 'Global Settings > Amazon S3 Settings > Amazon S3 bucket name',
            },
            'access_key_id': {
                'type': 'str',
                'required': False,
                'description': 'AWS Access Key Id to use to access [bucket_name]',
                'default': 'Global Settings > Amazon S3 Settings > AWS Access Key Id',
            },
            'secret_access_key': {
                'type': 'str',
                'required': False,
                'description': 'AWS Secret Access Key to use to access [bucket_name]',
                'default': 'Global Settings > Amazon S3 Settings > AWS Secret Access Key',
            },
            'preshared_key': {
                'type': 'str',
                'required': False,
                'description': 'Password to use to decrypt [key_name]',
                'default': 'Global Settings > Amazon S3 Settings > Backup encryption passphrase',
            },
            'allow_re_restore': {
                'type': 'bool',
                'required': False,
                'description': 'Restore [key_name] even if it has already been restored',
                'default': False,
            },
            'delete_backups': {
                'type': 'bool',
                'required': False,
                'description': 'Delete [key_name] from [bucket_name] after restore has finished',
                'default': False,
            },
        }

        root_master_settings = self.feature_flags_config().get(RootMasterNames.root_key) or {}
        aws_s3_settings = self._aws_s3_settings.copy()

        restore_opts = {}
        restore_opts['key_name'] = request_data.get('key_name')
        restore_opts['bucket_name'] = aws_s3_settings.get('bucket_name', None)
        restore_opts['preshared_key'] = aws_s3_settings.get('preshared_key', None)
        restore_opts['access_key_id'] = aws_s3_settings.get('aws_access_key_id', None)
        restore_opts['secret_access_key'] = aws_s3_settings.get('aws_secret_access_key', None)
        restore_opts['delete_backups'] = root_master_settings.get('delete_backups', False)
        restore_opts['allow_re_restore'] = request_data.get('allow_re_restore', False)

        if request_data.get('delete_backups', None) is not None:
            restore_opts['delete_backups'] = request_data['delete_backups']

        s3_keys = ['access_key_id', 'secret_access_key', 'bucket_name', 'preshared_key', 'access_key_id']
        for s3_key in s3_keys:
            if request_data.get(s3_key, None) is not None:
                restore_opts[s3_key] = request_data[s3_key]

        key_name = restore_opts['key_name']
        bucket_name = restore_opts['bucket_name']

        if not key_name:
            err = f'Must supply \'key_name\' of object in bucket {bucket_name!r}'
            return return_error(error_message=err, http_status=400, additional_data=explain)

        try:
            obj_meta = restore_from_s3_key(**restore_opts)

            try:
                obj_bytes = obj_meta['ContentLength']
                obj_gb = round(obj_bytes / (1024 ** 3), 3)
            except Exception:
                obj_gb = '???'

            return_data = {
                'status': 'success',
                'message': f'Successfully restored backup file',
                'additional_data': {
                    'bucket_name': bucket_name,
                    'key_name': key_name,
                    'key_size_gb': obj_gb,
                    'key_modified_dt': obj_meta.get('LastModified', None),
                    'key_deleted': obj_meta.get('deleted', None),
                    'key_re_restored': obj_meta.get('re_restored', None),
                },
            }

            return jsonify(return_data)
        except Exception as exc:
            err = f'Failure while restoring: {exc}'
            return return_error(error_message=err, http_status=400, additional_data=explain)
