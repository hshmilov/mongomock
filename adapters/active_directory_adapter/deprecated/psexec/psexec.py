"""psexec.py: Python script to enable some basic psexec commands.
   Works only on python 2.x !!!
"""

import sys
import logging
import string
import json

from impacket.dcerpc.v5 import transport
from impacket.smbconnection import SessionError
from impacket.examples import serviceinstall


# Some basic psexec exceptions
class FileExistsException(Exception):
    def __init__(self, message=""):
        super().__init__(message)


class PSEXEC(object):
    KNOWN_PROTOCOLS = {
        '445/SMB': (r'ncacn_np:%s[\pipe\svcctl]', 445),
        #'139/SMB': (r'ncacn_np:%s[\pipe\svcctl]', 139),
    }

    def __init__(self, protocols=None, username='', password='',
                 domain='', hashes=None, aesKey=None, doKerberos=False, kdcHost=None):
        self.__username = username
        self.__password = password
        if protocols is None:
            self.__protocols = PSEXEC.KNOWN_PROTOCOLS.keys()
        else:
            self.__protocols = [protocols]
        self.__domain = domain
        self.__lmhash = ''
        self.__nthash = ''
        self.__aesKey = aesKey
        self.__doKerberos = doKerberos
        self.__kdcHost = kdcHost
        if hashes is not None:
            self.__lmhash, self.__nthash = hashes.split(':')

        self.rpctransport = None

    def _init_connection(self, addr):
        for protocol in self.__protocols:
            protodef = PSEXEC.KNOWN_PROTOCOLS[protocol]
            port = protodef[1]

            logging.info("Trying protocol %s...\n" % protocol)
            stringbinding = protodef[0] % addr

            self.rpctransport = transport.DCERPCTransportFactory(stringbinding)
            self.rpctransport.set_dport(port)
            if hasattr(self.rpctransport, 'set_credentials'):
                # This method exists only for selected protocol sequences.
                self.rpctransport.set_credentials(self.__username, self.__password, self.__domain, self.__lmhash,
                                                  self.__nthash, self.__aesKey)

            self.rpctransport.set_kerberos(self.__doKerberos, self.__kdcHost)

    def send_file(self, src, dst_name):
        dce = self.rpctransport.get_dce_rpc()
        try:
            dce.connect()
        except Exception, e:
            logging.critical(str(e))
            sys.exit(1)

        connection = self.rpctransport.get_smb_connection()

        # Upload file
        logging.info("Uploading file %s" % dst_name)
        if isinstance(src, str):
            # We have a filename
            fh = open(src, 'rb')
        else:
            # We have a class instance, it must have a read method
            fh = src
        f = dst_name
        pathname = string.replace(f, '/', '\\')
        try:
            # This putFile is done inside the smbconnection.py file
            connection.putFile('ADMIN$', pathname, fh.read)
        except:
            logging.critical(
                "Error uploading file %s, aborting....." % dst_name)
            raise
        dce.disconnect()
        fh.close()

    def get_file(self, remote_path, local_path):
        fh = open(local_path, 'wb')

        dce = self.rpctransport.get_dce_rpc()
        try:
            dce.connect()
        except Exception, e:
            logging.critical(str(e))
            sys.exit(1)

        connection = self.rpctransport.get_smb_connection()

        pathname = string.replace(remote_path, '/', '\\')
        try:
            connection.getFile('ADMIN$', pathname, fh.write)
        except:
            logging.critical(
                "Error downloading file %s, aborting....." % remote_path)
            raise
        dce.disconnect()
        fh.close()

    def delete_file(self, remote_path):
        dce = self.rpctransport.get_dce_rpc()
        try:
            dce.connect()
        except Exception, e:
            logging.critical(str(e))
            sys.exit(1)

        connection = self.rpctransport.get_smb_connection()

        pathname = string.replace(remote_path, '/', '\\')
        try:
            connection.deleteFile('ADMIN$', pathname)
        except SessionError as se:
            if 'STATUS_OBJECT_NAME_NOT_FOUND' == se.getErrorString()[0]:
                # Exception is because the file does not exist
                print("file to delete does not exist")
            else:
                # Something else happened, raising the error
                raise
        except:
            logging.critical(
                "Error deleting file %s, aborting....." % remote_path)
            raise
        dce.disconnect()

    def execute_service(self, service_path):
        try:
            f = open(service_path, 'rb')
        except Exception as e:
            logging.critical(str(e))
            raise

        dce = self.rpctransport.get_dce_rpc()
        try:
            dce.connect()
        except Exception, e:
            logging.critical(str(e))
            sys.exit(1)

        installService = serviceinstall.ServiceInstall(
            self.rpctransport.get_smb_connection(), f)
        installService.install()
        f.close()
