from app.src.services.search_DOI_link_searched_state import SearchDOILinkedSearchedState
from app.src.services.search_DOI_state import SearchDOIState
from app.src.shared.helper import search_in_text


class SearchDOIReplacedState(SearchDOIState):
    def __init__(self, search_doi_service):
        super().__init__(search_doi_service)

    def to_string(self):
        return "replaced"

    def search_link(self, link, logging_service):
        search_in_text(link.location_replace_url, link)
        if link.doi:
            logging_service.logger.debug("DOI found in link")

        self.search_doi_service.to_state(SearchDOILinkedSearchedState(self.search_doi_service))