import logging
logger = logging.getLogger(f"axonius.{__name__}")

import os
import tempfile
import smtplib

from email.message import EmailMessage
from axonius.consts import email_consts


class EmailServer(object):

    def __init__(self, host, port, user=None, password=None, key=None, cert=None, source=None):
        """

        :param str host: Host of the smtp server.
        :param int port: Port of the smtp server.
        :param str user: The user to login to the smtp server with.
        :param str password: The password to login to the smtp server with.
        :param key: The key file to communicate in TLS with the smtp server with.
        :param cert: The certificate file to communicate in TLS with the smtp server with.
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
        self.key = bytes(key) if key is not None and key != '' else None
        self.cert = bytes(cert) if cert is not None and cert != '' else None
        self.source = source
        self._smtp = None

    def new_email(self, subject, recipients):
        return Email(self, subject, recipients)

    def __enter__(self):
        assert self._smtp is None
        try:
            server = smtplib.SMTP(self.host, self.port)
            if self.user:
                server.login(self.user, self.password)

            if self.key or self.cert:
                key_file_path = None
                cert_file_path = None
                try:
                    if self.key:
                        key_file_descriptor, key_file_path = tempfile.mkstemp()
                        with os.fdopen(key_file_descriptor, 'wb') as key_file:
                            key_file.write(self.key)

                    if self.cert:
                        cert_file_descriptor, cert_file_path = tempfile.mkstemp()
                        with os.fdopen(cert_file_descriptor, 'wb') as cert_file:
                            cert_file.write(self.cert)

                    server.starttls(key_file_path, cert_file_path)

                finally:
                    if key_file_path:
                        os.remove(key_file_path)

                    if cert_file_path:
                        os.remove(cert_file_path)
        except Exception:
            logger.exception("Exception was raised while trying to connect to e-mail server and send e-mail.")
            raise
        self._smtp = server

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._smtp is not None:
            try:
                self._smtp.quit()
            except Exception:
                logger.exception("Exception was raised while trying to quit the e-mail server connection.")
            self._smtp = None


class Email(object):

    def __init__(self, server: EmailServer, subject: str, recipients: list):
        assert isinstance(server, EmailServer)
        assert isinstance(subject, str)
        assert isinstance(recipients, list) and len(recipients) > 0
        self.server = server
        self.subject = subject
        self.recipients = recipients
        self.attachments = {}

    def add_attachment(self, name: str, data: bytes, mime_type: str):
        assert isinstance(name, str)
        assert isinstance(data, bytes)
        assert name not in self.attachments
        assert isinstance(mime_type, str) and '/' in mime_type
        self.attachments[name] = (data, mime_type)

    def add_pdf(self, name: str, data: bytes):
        self.add_attachment(name, data, 'application/pdf')

    def send(self, html_content: str):
        assert isinstance(html_content, str)
        msg = EmailMessage()
        msg['Subject'] = self.subject
        msg['From'] = self.server.source
        msg['To'] = ", ".join(self.recipients) if len(self.recipients) > 1 else self.recipients[0]
        msg.add_alternative(html_content, subtype='html')

        for name, value in self.attachments.items():
            data, mime = value
            mimetype, subtype = mime.split('/')
            msg.add_attachment(data, maintype=mimetype, subtype=subtype, filename=name)

        try:
            with self.server:
                self.server._smtp.send_message(msg)
        except Exception:
            logger.exception("Exception was raised while trying to connect to e-mail server and send e-mail.")
