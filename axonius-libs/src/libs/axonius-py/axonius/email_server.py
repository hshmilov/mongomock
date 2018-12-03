# pylint: disable=protected-access
import logging
import smtplib
import ssl
from email.message import EmailMessage

from axonius.types.ssl_state import SSLState

from axonius.utils.files import create_temp_file

from axonius.consts import email_consts

logger = logging.getLogger(f'axonius.{__name__}')


class EmailServer:

    def __init__(self, host, port, user=None, password=None,
                 ssl_state: SSLState = SSLState.Unencrypted, keyfile_data=None, certfile_data=None, ca_file_data=None,
                 source=None):
        """

        :param str host: Host of the smtp server.
        :param int port: Port of the smtp server.
        :param str user: The user to login to the smtp server with.
        :param str password: The password to login to the smtp server with.
        :parma ssl_state: How far to use SSL
        :param keyfile_data: Keyfile for TLS
        :param certfile_data: Cert file for TLS
        :param ca_file_data: CA File to trust in TLS
        :param str source: An email address to send emails from (currently defaults to system@axonius.com).
        """
        if source is None:
            source = email_consts.mail_from_address
        if user is not None:
            password = password or ''
        logger.info(f'email host: {host}')
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.__ssl_state = ssl_state
        self.__key_file = create_temp_file(keyfile_data) if keyfile_data else None
        self.__cert_file = create_temp_file(certfile_data) if certfile_data else None
        self.__ca_file = create_temp_file(ca_file_data) if ca_file_data else None

        self.source = source
        self.smtp = None

    def new_email(self, subject, to_recipients, cc_recipients=None):
        return Email(self, subject, to_recipients, cc_recipients)

    def __enter__(self):
        assert self.smtp is None
        try:
            server = smtplib.SMTP(self.host, self.port)

            # First activate TLS if available
            if self.__ssl_state != SSLState.Unencrypted:
                # First with provided TLS data
                context = ssl._create_stdlib_context(
                    certfile=self.__cert_file.name,
                    keyfile=self.__key_file.name,
                    cafile=self.__ca_file.name,
                    cert_reqs=ssl.CERT_REQUIRED if self.__ssl_state == SSLState.Verified else ssl.CERT_NONE)
                server.starttls(context=context)
            else:
                # Try TLS anyway because it's more secure
                try:
                    server.starttls()
                except Exception:
                    logger.info('Could not start TLS')

            # Try to login if optional.
            if self.user:
                server.login(self.user, self.password)
        except Exception:
            logger.exception('Exception was raised while trying to connect to e-mail server and send e-mail.')
            raise
        self.smtp = server

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.smtp is not None:
            try:
                self.smtp.quit()
            except Exception:
                logger.exception('Exception was raised while trying to quit the e-mail server connection.')
            self.smtp = None


class Email:

    def __init__(self, server: EmailServer, subject: str, to_recipients: list, cc_recipients: list):
        assert isinstance(server, EmailServer)
        assert isinstance(subject, str)
        assert isinstance(to_recipients, list) and len(to_recipients) > 0
        self.server = server
        self.subject = subject
        self.to_recipients = to_recipients
        self.cc_recipients = cc_recipients
        self.attachments = {}
        self.logos_attachments = {}

    def add_attachment(self, name: str, data: bytes, mime_type: str):
        assert isinstance(name, str)
        assert isinstance(data, bytes)
        assert name not in self.attachments
        assert isinstance(mime_type, str) and '/' in mime_type
        self.attachments[name] = (data, mime_type)

    def add_logos_attachments(self, data, maintype, subtype, cid):
        self.logos_attachments[cid] = (data, maintype, subtype)

    def add_pdf(self, name: str, data: bytes):
        self.add_attachment(name, data, 'application/pdf')

    def send(self, html_content: str):
        assert isinstance(html_content, str)

        msg = EmailMessage()

        msg['Subject'] = self.subject
        msg['From'] = self.server.source
        msg['To'] = ', '.join(self.to_recipients)
        if self.cc_recipients:
            msg['CC'] = ', '.join(self.cc_recipients)
        msg.add_alternative(html_content, subtype='html')

        if self.logos_attachments:
            for cid, value in self.logos_attachments.items():
                data, maintype, subtype = value
                msg.add_attachment(data, maintype=maintype, subtype=subtype, cid=cid)

        for name, value in self.attachments.items():
            data, mime = value
            mimetype, subtype = mime.split('/')
            msg.add_attachment(data, maintype=mimetype, subtype=subtype, filename=name)

        try:
            with self.server:
                self.server.smtp.send_message(msg)
        except Exception:
            logger.exception('Exception was raised while trying to send an e-mail.')
            raise
