from app.src.services.search_DOI_state import SearchDOIState


class SearchDOIEmbeddedSearchedState(SearchDOIState):
    def __init__(self, search_doi_service):
        super().__init__(search_doi_service)

    def to_string(self):
        return "embedded searched"