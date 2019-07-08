import os
import uuid
import mailbox
import errno

from typing import Iterable

from services.standalone_services.smtp_server import SMTPService


def generate_test_random_valid_email() -> str:
    """
    Generates a valid, random and unique email address
    """
    return f'test@{uuid.uuid4().hex}.ru'


def create_maildir_folders():
    try:
        os.makedirs('/tmp/mail_dir/new/')
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise
    try:
        os.makedirs('/tmp/mail_dir/cur/')
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise
    try:
        os.makedirs('/tmp/mail_dir/tmp/')
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise


class MailDiranasaurusService(SMTPService):

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

           CMD ["/go/src/github.com/flashmob/maildiranasaurus/maildiranasaurus", "serve"]
           '''[1:]

    def get_email_sent(self) -> Iterable[str]:
        """
        Get all lines from the syslog
        """
        out, _, _ = self.get_file_contents_from_container('/var/log/maildiranasaurus.log')
        return out.splitlines()

    def get_email_first_csv_content(self):
        """
        Get the first csv attachment content of the mail that was sent
        :return:
        """
        mail_name, _, _ = self.get_folder_content_from_container('/tmp/mail_dir/new')
        file_name = mail_name.decode('utf-8').strip()
        out, _, _ = self.get_file_contents_from_container(f'/tmp/mail_dir/new/{file_name}')
        assert out

        create_maildir_folders()

        local_file_name = f'/tmp/mail_dir/new/{file_name}'

        with open(local_file_name, 'wb') as file:
            file.write(out)

        m = mailbox.Maildir('/tmp/mail_dir')
        for key in m.iterkeys():
            message = m.get_message(key)
            # get the third message in the payload -
            # the first is the content and the 2nd is the pdf, the 3rd is the csv
            return message.get_payload()[2].get_payload(decode=True)

    def get_emails_sent(self) -> Iterable[str]:
        """
        Get all lines from the syslog
        """
        out, _, _ = self.get_file_contents_from_container('/var/log/maildiranasaurus.log')
        return out.splitlines()

    @property
    def image(self):
        return 'maildiranasaurus_server'
