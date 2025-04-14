from app.src.domain.common.entity import Entity


class EmailBody(Entity):
    def __init__(self, body, log_message="", is_parsed=False, is_google_scholar_format=False):
        self.text_html = body
        self.log_message = log_message
        self.is_parsed = is_parsed
        self.is_google_scholar_format = is_google_scholar_format
        super().__init__()

    def parse_body(self):
        self.is_parsed = True
