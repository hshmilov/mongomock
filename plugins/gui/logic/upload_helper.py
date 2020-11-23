import os
import logging
import secrets

import magic

from axonius.consts.gui_consts import IMAGE_MIME_TYPES
from axonius.consts.plugin_consts import MASTER_INSTANCE_CONTROL_PLUGIN_UNIQUE_NAME
from axonius.plugin_base import PluginBase
from axonius.plugin_exceptions import InvalidRequestException
from axonius.utils.files import UPLOADED_FILES_DIR, UPLOADED_HOST_FILES_DIR

logger = logging.getLogger(f'axonius.{__name__}')


def upload_file(field_name, file):
    validate_file(field_name, file)
    filename = file.filename

    written_file = PluginBase.Instance.db_files.upload_file(file, filename=filename)
    return {'uuid': str(written_file)}


def upload_image_file(field_name, file):
    validate_file(field_name, file)
    mimetype = file.content_type
    if mimetype not in IMAGE_MIME_TYPES:
        raise InvalidRequestException('Image upload failed: unsupported file type')
    file_buffer = file.read()
    if len(file_buffer) / 1000000 > 5:
        raise InvalidRequestException('Image upload failed : file size exceeded maximum size')
    with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
        if m.id_buffer(file_buffer) not in IMAGE_MIME_TYPES:
            raise InvalidRequestException('Image upload failed: unsupported file type')
    filename, file_extension = os.path.splitext(file.filename)
    file_to_convert = f'{secrets.token_hex(nbytes=10)}{file_extension}'
    converted_file_name = f'{secrets.token_hex(nbytes=10)}.png'
    temporary_file_path = os.path.join(UPLOADED_FILES_DIR, file_to_convert)
    target_path = os.path.join(UPLOADED_FILES_DIR, converted_file_name)
    try:
        file.seek(0)
        file.save(temporary_file_path)
        # pylint: disable=protected-access
        PluginBase.Instance._trigger_remote_plugin(
            MASTER_INSTANCE_CONTROL_PLUGIN_UNIQUE_NAME,
            job_name='run:imagemagick',
            data={'image_folder': UPLOADED_HOST_FILES_DIR,
                  'source': file_to_convert, 'target': converted_file_name},
            stop_on_timeout=False,
            priority=True
        )
        written_file = None
        with open(target_path, 'rb') as target_file:
            written_file = PluginBase.Instance.db_files.upload_file(target_file, filename=f'{filename}{file_extension}')
        return {'uuid': str(written_file)}
    except Exception as e:
        logger.exception(e)
        raise InvalidRequestException('Image upload failed: invalid image')
    finally:
        os.remove(temporary_file_path)
        os.remove(target_path)


def validate_file(field_name, file):
    if not field_name:
        raise InvalidRequestException('Field name must be specified')
    if not file or file.filename == '':
        raise InvalidRequestException('File must exist')
