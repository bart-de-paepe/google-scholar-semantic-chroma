import json
import re
from time import sleep

import crossref_commons.sampling

from app.src.services.search_DOI_crossref_searched_state import SearchDOICrossrefSearchedState
from app.src.services.search_DOI_state import SearchDOIState
from app.src.shared.helper import do_external_request, search_in_text, search_in_pdf


class SearchDOILinkedSearchedState(SearchDOIState):
    def __init__(self, search_doi_service):
        super().__init__(search_doi_service)

    def to_string(self):
        return "link searched"

    def search_crossref(self, link, title, logging_service):
        sleep(5) # wait 5 seconds to avoid sending too many requests
        try:
            filter = {}
            queries = {'query.title': title}
            response = crossref_commons.sampling.get_sample(size=2, filter=filter, queries=queries)
            logging_service.logger.debug(json.dumps(response))
            crossref_match = False
            for record in response:
                if not crossref_match:
                    crossref_title = record['title'][0]
                    crossref_title = self.process_title(crossref_title)
                    title = self.process_title(title)

                    if crossref_title == title:
                        link.doi = record['DOI']
                        link.is_doi_success = True
                        crossref_match = True
                        logging_service.logger.debug('DOI: ' + link.doi)
                        logging_service.logger.debug("DOI found in link")
                    else:
                        logging_service.logger.debug('DOI is None')

        except ValueError as e:
            logging_service.logger.error('ValueError: ' + str(e))
        except ConnectionError as e:
            logging_service.logger.error('ConnectionError: ' + str(e))
            """
            self.logging_service.logger.debug(
                f'crossref for search result: {link_id} parsed and stored in database')
            """
        finally:
            self.search_doi_service.to_state(SearchDOICrossrefSearchedState(self.search_doi_service))

    def process_title(self, title):
        title = title.lower()
        title = re.sub(r'[^a-zA-Z0-9\s]', '', title)
        return title
