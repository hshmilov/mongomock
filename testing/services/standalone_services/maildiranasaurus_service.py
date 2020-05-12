import os
import mailbox
import errno

from services.standalone_services.smtp_service import SmtpService


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

           CMD ["/go/src/github.com/flashmob/maildiranasaurus/maildiranasaurus", "serve"]
           '''[1:]

    def get_mail_folder(self):
        mail_name, _, _ = self.get_folder_content_from_container('/tmp/mail_dir/new')
        file_name = mail_name.decode('utf-8').strip()
        out, _, _ = self.get_file_contents_from_container(f'/tmp/mail_dir/new/{file_name}')
        assert out

        create_maildir_folders()

        local_file_name = f'/tmp/mail_dir/new/{file_name}'

        with open(local_file_name, 'wb') as file:
            file.write(out)

        return mailbox.Maildir('/tmp/mail_dir')

    def get_mail_message(self, recipient):
        """
        Get the whole mail message for the recipient
        :return:
        """
        m = self.get_mail_folder()
        payload = None
        for key in m.iterkeys():
            message = m.get_message(key)
            if message.get('To') != recipient:
                continue
            payload = message
            break
        m.clear()
        return payload

    def get_email_subject(self, recipient):
        message = self.get_mail_message(recipient)
        return message['subject']

    def get_email_first_csv_content(self, recipient):
        """
        Get the first csv attachment content of the mail that was sent
        :return:
        """
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
