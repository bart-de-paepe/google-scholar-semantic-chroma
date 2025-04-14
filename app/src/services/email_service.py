import email
import imaplib
import os
import re
from datetime import datetime, timezone
from email.header import make_header, decode_header

from dotenv import load_dotenv

from app.src.domain.email import Email
from app.src.services.db_service import DBService
from app.src.services.logging_service import LoggingService
from app.src.shared.helper import escape_double_quotes, printable_date_time_now

load_dotenv()
MAIL_SERVER = os.getenv('MAIL_SERVER')
MAIL_SERVER_PORT = os.getenv('MAIL_SERVER_PORT')
MAIL_ADDRESS = os.getenv('MAIL_ADDRESS')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')

class EmailService:
    def __init__(self, db_service: DBService, logging_service: LoggingService):
        self.db_service = db_service
        self.logging_service = logging_service

    def connect_and_login(self):
        """Connects to mail server using given credentials."""
        try:
            mail_host = imaplib.IMAP4_SSL(MAIL_SERVER)
            mail_host.login(MAIL_ADDRESS, MAIL_PASSWORD)
            return mail_host
        except imaplib.IMAP4.error as error:
            raise ConnectionError(error)

    def get_unread_ids(self, mail_host):
        """Fetches unread email IDs from within the inbox."""
        try:
            mail_host.select('inbox')
        except imaplib.IMAP4.error:
            print('Could not select inbox')
            return []
        _, unread = mail_host.search(None, '(UNSEEN)')
        unread_email_ids = unread[0].split()
        return unread_email_ids

    def fetch_email_content(self, mailbox, email_id):
        """Fetches the content of the emails from within the inbox for each email ID."""
        _, data = mailbox.fetch(email_id, '(RFC822)')
        raw_email = data[0][1]
        return email.message_from_bytes(raw_email)

    def parse_email(self, email_message):
        """Parses for relevant information being sought from each email."""
        sender = str(make_header(decode_header(email_message['From'])))
        subject = str(make_header(decode_header(email_message['Subject'])))
        datetime_str = email_message['Date']
        date_sent = datetime.strptime(datetime_str, '%a, %d %b %Y %H:%M:%S %z')
        email_body = ""

        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == 'text/html':
                    email_body = part.get_payload(decode=True).decode()
                    break
        else:
            email_body = email_message.get_payload(decode=True).decode()
        current_email = Email(sender, date_sent, subject, email_body)
        current_email.check_spam()
        db_email_id = self.store_email_content(current_email)
        self.logging_service.logger.debug(f'email id: {db_email_id} parsed and stored in database')
        return {'current_email': current_email, 'db_email_id': db_email_id}

    def store_email_content(self, current_email: Email):
        current_email.log_message = "Email read successfully."
        if current_email.is_spam:
            current_email.log_message = "Email is spam."
        post = {
            "created_at": current_email.get_created_at_formatted(),
            "updated_at": current_email.get_updated_at_formatted(),
            "sender": current_email.sender,
            "date_time": current_email.get_datetime_formatted(),
            "subject": escape_double_quotes(current_email.subject),
            "body": {
                "text_html": escape_double_quotes(current_email.body.text_html),
            },
            "is_processed": current_email.is_processed,
            "is_spam": current_email.is_spam,
            "log_message": current_email.log_message,
        }
        self.db_service.set_collection("emails")
        post_id = self.db_service.insert_one(post)
        return post_id

    def update_email(self, email_update_what, email_update_where):
        self.db_service.set_collection("emails")
        result = self.db_service.update_one_what_where(email_update_what, email_update_where)

    def move_email(self, current_email: Email, mailbox, email_id):
        mailboxname = current_email.subject

        if current_email.is_spam:
            mailboxname = "Spam"
        else:
            match = re.search(r'"([^"]*)"', current_email.subject)  # search the first occurence of text between double quotes
            if match is not None:
                mailboxname = match.group(1).replace(' ', '-')
            else:
                match = re.search(r'^[^:]+', current_email.subject)  # match everything before colon (:)
                if match is not None:
                    mailboxname = match.group(0).replace(' ', '-')

        mailbox.copy(email_id, mailboxname)
        mailbox.store(email_id, '+FLAGS', r'(\Deleted)')

    def get_current_email(self, email_id):
        self.db_service.set_collection("emails")
        result = self.db_service.select_one(email_id)
        date_sent = datetime.strptime(result['date_time'], "%Y-%m-%dT%H:%M:%SZ")
        current_email = Email(result['sender'], date_sent, result['subject'], result['body']['text_html'])
        return current_email

    def log(self, message):
        self.logging_service.logger.debug(f'{printable_date_time_now()}: {message}')
