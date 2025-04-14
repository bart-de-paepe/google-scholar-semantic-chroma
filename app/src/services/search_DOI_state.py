from abc import ABC  # Abstract Base Class
def get_all_states():
    return ["unprocessed", "replaced", "link_searched", "content_searched", "embedded_searched"]

class SearchDOIState(ABC):
    def __init__(self, search_doi_service):
        self.search_doi_service = search_doi_service

    def replace(self, link, logging_service):
        print("You can't replace")

    def search_link(self, link, logging_service):
        print("You can't search link")

    def search_content(self, link, media_type, logging_service):
        print("You can't search content")

    def search_embedded(self, link, logging_service):
        print("You can't search embedded")

    def to_string(self):
        pass