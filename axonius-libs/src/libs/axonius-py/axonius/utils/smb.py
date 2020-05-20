import logging
from socket import gethostname

# pylint: disable=import-error
from smb.SMBConnection import SMBConnection
# pylint: disable=import-error
from smb import smb_structs

logger = logging.getLogger(f'axonius.{__name__}')


class SMBClient:
    """
    Create, initialize and connect a general-purpose SMB client. The
    only required information is a host name, IP address (in case DNS
    lookups are not possible) and the share name. The share name can
    include the share path (i.e. "smb_share_name/share/path"), since the
    _process_share function will split it up and format it.
    """

    def __init__(self, ip: str,
                 smb_host: str,
                 share_name: str,
                 username: str = None,
                 password: str = None,
                 port: int = 445,
                 use_nbns: bool = True):

        if not isinstance(ip, str):
            raise ValueError(f'IP is not a string, but {type(ip)}')
        self._ip = ip

        if not isinstance(smb_host, str):
            raise ValueError(f'SMB host is not a string, but {type(smb_host)}')
        self._smb_host = smb_host

        if not isinstance(share_name, str):
            raise ValueError(f'SMB share name is not a string, but {type(share_name)}')
        self._process_share(share_name=share_name)

        if not self._directory_path:
            self._directory_path = '/'

        if not isinstance(username, str):
            raise ValueError(f'Username is not a string, but {type(username)}')
        self._username = username.replace('\\', '/')

        if not isinstance(password, str):
            raise ValueError(f'Password is not a string, but {type(password)}')
        self._password = password

        if not isinstance(port, int):
            raise ValueError(f'Port is not an integer, but {type(port)}')
        self._port = port

        if not isinstance(use_nbns, bool):
            raise ValueError(f'Use NBNS is not a boolean, but {type(use_nbns)}')

        if use_nbns:
            self._is_direct_tcp = False
        else:
            self._is_direct_tcp = True

        self._set_localhost()
        self._server = None

        self._connect()

    def _connect(self):
        """ Connect to the SMB share. """
        self._server = SMBConnection(username=self._username,
                                     password=self._password,
                                     my_name=self._host,
                                     remote_name=self._smb_host,
                                     use_ntlm_v2=True,
                                     is_direct_tcp=self._is_direct_tcp)
        try:
            self._server.connect(self._ip, port=self._port)
        except Exception:
            logger.exception(f'Could not connect to the SMB Share: '
                             f'{self._host} @ {self._ip}')
            raise

    def delete_files_from_smb(self, files: list, directory_path: str = None):
        """
        Delete files from the SMB share. The caller can send a
        directory_path that is different from the original client.

        :param list files: A list of filenames to delete. They must be
        in the same *directory_path.
        :param str directory_path: The pathname/directory/folder that
        contains the list of *files.
        """
        if not directory_path:
            directory_path = self._directory_path

        if not directory_path.endswith('/'):
            directory_path = f'{directory_path}/'

        for file in files:
            path_with_file = f'{directory_path}{file}'
            try:
                self._server.deleteFiles(self._share_name, path_with_file)
                logger.info(f'Deleted {path_with_file} from {self._share_name}')
            except smb_structs.OperationFailure:
                logger.warning(f'Delete failed. File '
                               f'{self._share_name}{path_with_file} not found.')
            except Exception:
                logger.exception(f'Unable to delete {directory_path}{file} from'
                                 f' {self._share_name}')

    def download_files_from_smb(self, files: list, directory_path: str = None):
        """
        Download files from the remote share. The caller can send a
        directory_path that is different from the original client.

        :param list files: A list of filenames to download. The files
        must be in the same *directory_path.
        :param str directory_path: The pathname/directory/folder that
        contains the list *files.
        """
        if not directory_path:
            directory_path = self._directory_path

        if not directory_path.endswith('/'):
            directory_path = f'{directory_path}/'

        for file in files:
            try:
                with open(file, 'wb') as file_obj:
                    path_with_file = f'{directory_path}{file}'
                    self._server.retrieveFile(service_name=self._share_name,
                                              path=path_with_file,
                                              file_obj=file_obj)
                logger.info(f'Downloaded {file} from {self._share_name}')
            except smb_structs.OperationFailure:
                logger.warning(f'Download failed. File '
                               f'{self._share_name}{directory_path}{file} not found.')
            except Exception:
                logger.exception(f'Unable to download {directory_path}{file} from'
                                 f' {self._share_name}')

    def list_files_on_smb(self, directory_path: str = None) -> list:
        """
        List files on the SMB share. The caller can send a
        directory_path that is different from the original client.

        :param str directory_path: The pathname/directory/folder that we want
        to list.
        :returns: A list of filenames found on *directory_path. "." and ".."
        are filtered out of the response.
        """
        if not directory_path:
            directory_path = self._directory_path

        if not directory_path.endswith('/'):
            directory_path = f'{directory_path}/'

        return [f.filename for f in self._server.listPath(self._share_name, directory_path)
                if not f.filename.startswith('.')] or []

    def _process_share(self, share_name: str):
        """
        Take the passed *share_name and split it up into the actual share
        name and the path. Do some fancy replacements and make sure that
        there is a trailing '/' at the end of the directory_path.

        :param str share_name: A route to the folder/directory/share that we'd
        like to use. This can be in '\', '\\', '/' or escaped style.
        """
        if share_name.startswith('\\\\'):
            share_name = share_name[2:]

        shares = share_name.replace('\\', '/')

        while shares.startswith('/'):
            shares = shares[1:]

        while shares.endswith('/'):
            shares = shares[:-1]

        shares_temp = shares.split('/')

        self._share_name = shares_temp[0]

        if len(shares_temp) > 1:
            self._directory_path = f'/{"/".join(shares_temp[1:])}/'
        else:
            self._directory_path = '/'

    def _set_localhost(self):
        """
        Get the name of the localhost and set it in our scope. This is
        used in the _connect phase.
        """
        try:
            host = gethostname()
        except Exception as err:
            logger.exception(f'Unable to query for the hostname: {err}')

        if isinstance(host, str):
            self._host = host
        else:
            self._host = 'local-machine'
            logger.warning(f'Hostname not parsable for {host}')

    def upload_files_to_smb(self, files: list, directory_path: str = None):
        """
        Upload files to the SMB share. The caller can send a
        directory_path that is different from the original client.

        :param list files: A list of filenames to upload. They must be
        in the same *directory_path.
        :param str directory_path: The pathname/directory/folder that we'd
        like to use to upload the list of *files.
        """
        if not directory_path:
            directory_path = self._directory_path

        if not directory_path.endswith('/'):
            directory_path = f'{directory_path}/'

        for file in files:
            try:
                with open(file, 'rb') as file_obj:
                    path_with_file = f'{directory_path}{file}'
                    self._server.storeFile(service_name=self._share_name,
                                           path=path_with_file,
                                           file_obj=file_obj)
                logger.info(f'Uploaded {file} to {self._share_name}')
            except FileNotFoundError:
                logger.error(f'Upload failed. File '
                             f'{self._share_name}{directory_path}{file} not '
                             f'writable.')
            except Exception:
                logger.exception(f'Unable to upload {directory_path}{file} to'
                                 f' {self._share_name}')
