import re

from app.src.domain.link import Link
from app.src.domain.sciencedirect_link import ScienceDirectLink
from app.src.services.db_service import DBService
from app.src.services.logging_service import LoggingService
from app.src.services.search_DOI_unprocessed_state import SearchDOIUnprocessedState


class SearchDOIService:
    def __init__(self, db_service: DBService, logging_service: LoggingService):
        self.db_service = db_service
        self.logging_service = logging_service
        self.current_state = SearchDOIUnprocessedState(self)
        self.link = None

    # query all the unprocessed _id's
    def get_unprocessed_ids(self):
        where = {"is_processed": False}
        what = {"_id": 1}
        self.db_service.set_collection("search_results")
        unprocessed_ids = self.db_service.select_what_where(what, where)
        return unprocessed_ids

    # for every _id get the corresponding document link
    def get_link_and_media_type(self, search_result_id):
        where = {"_id": search_result_id}
        what = {"link": 1, "_id": 0, "media_type": 1}
        self.db_service.set_collection("search_results")
        link_cursor = self.db_service.select_what_where(what, where)
        link = link_cursor.next()
        if 'media_type' in link:
            link_and_media_type_object = {"link": Link(url=link['link']['url']), "media_type": link['media_type']}
        else:
            link_and_media_type_object = {"link": Link(url=link['link']['url']), "media_type": ""}
        link_cursor.close()
        return link_and_media_type_object

    def get_link(self):
        return self.link

    def set_link(self, link):
        self.link = link

    def next_step(self, link_and_media_type):
        match(self.current_state.to_string()):
            case "unprocessed":
                self.replace()
                return self.link
            case "replaced":
                link = self.check_link_template()
                self.set_link(link)
                self.search_link()
                return self.link
            case "link searched":
                media_type = link_and_media_type['media_type']
                self.search_content(media_type)
                return self.link
            case "content searched":
                self.search_embedded()
                return self.link


    def to_state(self, search_doi_state):
        self.current_state = search_doi_state

    def reset_state(self):
        self.current_state = SearchDOIUnprocessedState(self)

    def processing_finished(self):
        return self.current_state.to_string().lower() == "embedded searched"

    def replace(self):
        self.current_state.replace(self.link, self.logging_service)

    def check_link_template(self):
        if re.search("https://www.sciencedirect.com/science/article/pii/", self.link.location_replace_url):
            return ScienceDirectLink(self.link.url, self.link.location_replace_url)
        return self.link

    def search_link(self):
        self.current_state.search_link(self.link, self.logging_service)

    def search_content(self, media_type):
        self.current_state.search_content(self.link, media_type, self.logging_service)

    def search_embedded(self):
        self.current_state.search_embedded(self.link, self.logging_service)

    def update_link_content(self, search_result_id):
        search_result_update_where = {
            "_id": search_result_id,
        }
        search_result_update_what = {
            "link": {
                "url": self.link.url,
                "location_replace_url": self.link.location_replace_url,
                "response_code": self.link.response_code,
                "response_type": self.link.response_type,
                "is_accepted_type": self.link.is_accepted_type,
                "DOI": self.link.doi,
                "log_message": self.link.log_message,
                "is_DOI_success": self.link.is_doi_success,
                "is_processed": False
            },
        }
        self.db_service.set_collection("search_results")
        result = self.db_service.update_one_what_where(search_result_update_what, search_result_update_where)
        self.logging_service.logger.debug(f'doi for search result: {search_result_id} parsed and stored in database')

