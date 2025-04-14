import os
import re
from abc import ABC

from dotenv import load_dotenv

from app.src.domain.common.entity import Entity

load_dotenv()
CONTENT_TYPE_HTML = os.getenv('CONTENT_TYPE_HTML')
CONTENT_TYPE_PDF = os.getenv('CONTENT_TYPE_PDF')


class AbstractLink(Entity, ABC):
    def __init__(self, url="", location_replace_url="", response_code=0, response_type="", is_accepted_type=False,
                 doi="", log_message="", is_doi_success=False, is_processed=False):
        super().__init__()
        self.url = url
        self.location_replace_url = location_replace_url
        self.response_code = response_code
        self.response_type = response_type
        self.is_accepted_type = is_accepted_type
        self.doi = doi
        self.log_message = log_message
        self.is_doi_success = is_doi_success
        self.is_processed = is_processed

    def check_accepted_type_html(self):
        pattern = CONTENT_TYPE_HTML
        if re.search(pattern, self.response_type, re.IGNORECASE):
            self.response_type = CONTENT_TYPE_HTML
            self.is_accepted_type = True
            return True
        else:
            return False

    def check_accepted_type_pdf(self):
        pattern = CONTENT_TYPE_PDF
        if re.search(pattern, self.response_type, re.IGNORECASE):
            self.response_type = CONTENT_TYPE_PDF
            self.is_accepted_type = True
            return True
        else:
            return False
