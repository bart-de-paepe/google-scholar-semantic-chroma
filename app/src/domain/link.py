from app.src.domain.abstract_link import AbstractLink
from app.src.shared.helper import do_external_request

class Link(AbstractLink):
    def __init__(self, url="", location_replace_url="", response_code=0, response_type="", is_accepted_type=False,
                 doi="", log_message="", is_doi_success=False, is_processed=False):
        super().__init__(url, location_replace_url, response_code, response_type, is_accepted_type, doi, log_message, is_doi_success, is_processed)

    def do_request(self, logging_service):
        logging_service.logger.debug("LINK DO REQUEST")
        return do_external_request(self.location_replace_url, True)
