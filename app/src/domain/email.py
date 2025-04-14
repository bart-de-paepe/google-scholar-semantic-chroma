import os
import re

from dotenv import load_dotenv

from app.src.domain.common.entity import Entity
from app.src.domain.email_body import EmailBody

load_dotenv()
SENDER = os.getenv('SENDER')

class Email(Entity):
    def __init__(self, sender, datetime_obj, subject, body):
        self.sender = sender
        self.datetime = datetime_obj
        self.subject = subject
        self.body = EmailBody(body=body)
        self.log_message = ''
        self.is_processed = False
        self.is_spam = False
        super().__init__()

    def get_datetime_formatted(self):
        return self.datetime.strftime("%Y-%m-%dT%H:%M:%SZ")


    def check_spam(self):
        pattern = SENDER
        if re.search(pattern, self.sender, re.IGNORECASE):
            self.is_spam = False
        else:
            self.is_spam = True