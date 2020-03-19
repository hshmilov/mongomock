# Modified version of SMBHandler from smb.SMBHandler .
# See license and copyright information for pysmb at
# https://github.com/miketeo/pysmb/blob/master/LICENSE


import logging
import os
import sys
import socket
import urllib.request
import urllib.error
import urllib.parse
import mimetypes
import email
import tempfile
from urllib.parse import (unwrap, unquote, splittype, splithost,
                          splitport, splittag, splitattr, splituser, splitpasswd, splitvalue)
from urllib.response import addinfourl
from smb.SMBConnection import SMBConnection

from io import BytesIO

from smb.SMBHandler import SMBHandler

from axonius.utils import dns

logger = logging.getLogger(f'axonius.{__name__}')

USE_NTLM = True
MACHINE_NAME = None


def get_smb_handler(use_nbns=True):
    if use_nbns:
        return SMBHandler
    return AlternateSMBHandler


class AlternateSMBHandler(urllib.request.BaseHandler):

    def smb_open(self, req):
        global USE_NTLM, MACHINE_NAME

        if not req.host:
            raise urllib.error.URLError('SMB error: no host given')
        host, port = splitport(req.host)
        if port is None:
            port = 445
        else:
            port = int(port)

        # username/password handling
        user, host = splituser(host)
        if user:
            user, passwd = splitpasswd(user)
        else:
            passwd = None
        host = unquote(host)
        user = user or ''

        domain = ''
        if ';' in user:
            domain, user = user.split(';', 1)

        passwd = passwd or ''
        myname = MACHINE_NAME or self.generateClientMachineName()

        # server_name = host.split('.')[0]
        logger.info(f'Querying ip for host {host}')
        host_ip = dns.query_dns(host, 30)
        server_name = host
        logger.info(f'Found host {server_name} with ip {host_ip}')
        path, attrs = splitattr(req.selector)
        if path.startswith('/'):
            path = path[1:]
        dirs = path.split('/')
        dirs = list(map(unquote, dirs))
        service, path = dirs[0], '/'.join(dirs[1:])

        try:
            conn = SMBConnection(user, passwd, myname, server_name, domain=domain,
                                 use_ntlm_v2=USE_NTLM, is_direct_tcp=True)
            conn.connect(host_ip, port)

            headers = email.message.Message()
            if req.data:
                filelen = conn.storeFile(service, path, req.data)

                headers.add_header('Content-length', '0')
                fp = BytesIO(b"")
            else:
                fp = self.createTempFile()
                file_attrs, retrlen = conn.retrieveFile(service, path, fp)
                fp.seek(0)

                mtype = mimetypes.guess_type(req.get_full_url())[0]
                if mtype:
                    headers.add_header('Content-type', mtype)
                if retrlen is not None and retrlen >= 0:
                    headers.add_header('Content-length', '%d' % retrlen)

            return addinfourl(fp, headers, req.get_full_url())
        except Exception as ex:
            raise urllib.error.URLError('smb error: %s' % ex).with_traceback(sys.exc_info()[2])

    def createTempFile(self):
        return tempfile.TemporaryFile()

    def generateClientMachineName(self):
        hostname = socket.gethostname()
        if hostname:
            return hostname.split('.')[0]
        return 'SMB%d' % os.getpid()
