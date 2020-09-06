import email
import glob
import os
import mailbox

from distutils.dir_util import copy_tree
from distutils.errors import DistutilsFileError

from axonius.utils.wait import wait_until
from services.standalone_services.smtp_service import SmtpService


class MaildiranasaurusService(SmtpService):

    @property
    def name(self):
        return 'maildiranasaurus'

    def get_dockerfile(self, *args, **kwargs):
        return fr'''
          FROM golang:1.11.2

           WORKDIR /go/src
           RUN curl https://raw.githubusercontent.com/golang/dep/master/install.sh | sh

           RUN git clone --depth=50 --branch=master https://github.com/flashmob/maildiranasaurus.git github.com/flashmob/maildiranasaurus

           WORKDIR /go/src/github.com/flashmob/maildiranasaurus

           RUN make dependencies

           RUN make maildiranasaurus || echo dependencies failed

           COPY goguerrilla ./

           VOLUME ["/opt/logs"]

           CMD ["/go/src/github.com/flashmob/maildiranasaurus/maildiranasaurus", "serve"]
           '''[1:]

    def get_mail_folder(self):
        mail_dir = os.path.join(self.log_dir, 'mail_dir')
        os.system(f'sudo chown -R ubuntu:ubuntu {mail_dir}')
        return mailbox.Maildir(mail_dir)

    def get_mail_message(self, recipient):
        """
        Get the whole mail message for the recipient
        :return:
        """
        m = self.get_mail_folder()
        try:
            # Hack, copy tmp content to new folder in case our mail mistakenly got there
            copy_tree(os.path.join(self.log_dir, 'mail_dir', 'tmp'), os.path.join(self.log_dir, 'mail_dir', 'new'))
        except DistutilsFileError:
            # if folder not exists yet we are fine with it
            pass
        payload = None
        for key in m.iterkeys():
            message = m.get_message(key)
            if message.get('To') != recipient:
                continue
            payload = message
            break
        return payload

    @property
    def volumes(self):
        return [f'{self.log_dir}:/opt/logs']

    def get_email_subject(self, recipient):
        message = self.get_mail_message(recipient)
        return message['subject']

    def wait_for_email_first_csv_content(self, recipient):
        try:
            return wait_until(self.get_email_first_csv_content,
                              check_return_value=True,
                              total_timeout=60 * 5,
                              recipient=recipient)
        except TimeoutError:
            # In case MailBox library fails...
            for email_file in glob.glob(f'{os.path.join(self.log_dir, "mail_dir")}/*/*'):
                with open(email_file, 'r') as fh:
                    try:
                        email_parsed = email.message_from_string(fh.read())
                    except Exception:
                        continue
                    if email_parsed.get('To') == recipient:
                        return self.get_email_first_csv_content(recipient, email_parsed)
            raise

    def get_email_first_csv_content(self, recipient, message=None):
        """
        Get the first csv attachment content of the mail that was sent
        :return:
        """
        if message is None:
            message = self.get_mail_message(recipient)
        if message:
            for attachment in message.get_payload():
                if attachment.get_content_type() == 'text/csv':
                    return attachment.get_payload(decode=True)
        return None

    def get_email_body(self, recipient: str) -> list:
        return self.get_mail_message(recipient).get_payload()

    @property
    def is_unique_image(self):
        return True
