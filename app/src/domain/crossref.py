from app.src.domain.common.entity import Entity

class Crossref(Entity):
    def __init__(self, response_code=0, is_valid_response=False, title="", author="", year=0, publisher="", log_message="", doi_url="",
                 api_url=""):
        super().__init__()
        self.response_code = response_code
        self.is_valid_response = is_valid_response
        self.title = title
        self.author = author
        self.year = year
        self.publisher = publisher
        self.log_message = log_message
        self.doi_url = doi_url
        self.api_url = api_url
