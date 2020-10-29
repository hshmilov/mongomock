import logging
import shutil
import uuid
from pathlib import Path

from flask import request, make_response
from werkzeug.utils import secure_filename

from axonius.utils.permissions_helper import PermissionCategory, PermissionAction, PermissionValue
from gui.logic.routing_helper import gui_section_add_rules, gui_route_logged_in
# pylint: disable=no-member,too-many-boolean-expressions,inconsistent-return-statements,no-else-return,too-many-branches

logger = logging.getLogger(f'axonius.{__name__}')


@gui_section_add_rules('configuration')
class Configuration:
    @gui_route_logged_in('upload_file', methods=['POST'], enforce_trial=False)
    def create_file_upload(self):
        """
        path: /api/settings/configuration
        """
        total, used, free = shutil.disk_usage(self.upload_files_dir)
        # make sure system will have at least 200M disk space
        margin = 200000000
        headers = request.headers
        # get total file size
        file_size = int(headers.get('Upload-Length', 0))
        if (file_size * 3) > (free - margin):
            return make_response(('No disk space', 500))
        # create file id
        file_id = str(uuid.uuid4())
        self.upload_files_list[file_id] = {
            'size': file_size,
            'name': None,
            'done': False,
        }
        # if file exist delete it
        file_path = Path(self.upload_files_dir, 'configuration_script.tar')
        if file_path.exists():
            file_path.unlink()

        logger.info(f'upload_file: request register id:{file_id}')
        return make_response((file_id, 200))

    @gui_route_logged_in('upload_file', methods=['PATCH'], enforce_trial=False, required_permission=PermissionValue.get(
        PermissionAction.Update, PermissionCategory.Settings), skip_activity=True)
    def upload_file(self):
        """
        Fetch the Getting Started checklist state from db
        """
        headers = request.headers
        file_id = request.args.get('patch')
        if not self.upload_files_list[file_id]:
            return make_response(('Trying to patch unauthorized file', 500))
        file_size = int(headers.get('Upload-Length', None))
        file_name = headers.get('Upload-Name', None)
        file_offset = int(headers.get('Upload-Offset', None))
        content_length = int(headers.get('Content-Length', None))
        data_to_write = request.data
        file_path = Path(self.upload_files_dir, 'configuration_script.tar')
        try:
            with file_path.open('ab') as f:
                f.seek(file_offset)
                f.write(data_to_write)
        except OSError:
            logger.error(f'could not write to file :{file_path}')
            return make_response(('could not write to file', 500))
        # are we done? ( last chunk ? )
        if file_offset + content_length == file_size:
            self.upload_files_list[file_id].update({
                'name': file_name,
                'done': True,
            })
        logger.debug(f'upload_file :{file_name} chunk from:{file_offset} length:{content_length}')
        return make_response((file_id, 200))

    @gui_route_logged_in('upload_file', methods=['DELETE'], enforce_trial=False,
                         required_permission=PermissionValue.get(PermissionAction.Update,
                                                                 PermissionCategory.Settings))
    def delete_uploaded_file(self):
        file_id = request.data.decode()
        if not file_id:
            return make_response((f'no file requested for delete', 500))
        if file_id not in self.upload_files_list:
            return make_response((f'wrong file_id :{file_id}', 500))

        file_name = self.upload_files_list[file_id].get('name')
        file_path = Path(self.upload_files_dir, secure_filename(file_name))
        if file_path.exists():
            file_path.unlink()
        del self.upload_files_list[file_id]
        return make_response((f'file {file_id} deleted', 200))

    @gui_route_logged_in('execute/<file_id>', methods=['POST'], enforce_trial=False)
    def execute_file(self, file_id):
        if file_id in self.upload_files_list:
            file_name = 'configuration_script.tar'
            file_path = Path(self.upload_files_dir, file_name)
            url = f'find_plugin_unique_name/nodes/{self.node_id}/plugins/instance_control'
            instance_control_name = self.request_remote_plugin(url).json().get('plugin_unique_name')
            resp = self.request_remote_plugin('file_execute',
                                              instance_control_name,
                                              method='post',
                                              raise_on_network_error=True,
                                              json={'path': str(file_path)})
            if resp.status_code != 200:
                logger.error(f'failure execute file '
                             f'error: {str(resp.content)} ')
            else:
                logger.info(f'file executed {file_id}')
                return make_response(('file executed', 200))

        return make_response((f'no file {file_id}', 400))
