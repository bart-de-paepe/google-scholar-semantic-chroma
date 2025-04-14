import json
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
            crossref_title = response[0]['title'][0]
            #print('crossref_title: ', crossref_title)
            if crossref_title == title:
                link.doi = response[0]['DOI']
                logging_service.logger.debug('DOI: ' + link.doi)
            else:
                link.doi = None
                logging_service.logger.debug('DOI is None')
            if link.doi:
                logging_service.logger.debug("DOI found in link")

        except ValueError as e:
            #crossref_object = Crossref(response_code=404, log_message='ValueError: ' + str(e), doi_url="https://doi.org/" + link.doi)
            logging_service.logger.error('ValueError: ' + str(e))
            #self.store_crossref(link_id, crossref_object)
        except ConnectionError as e:
            #all_numbers = re.findall(r'\d+', str(e))
            #crossref_object = Crossref(response_code=all_numbers[0], log_message='ConnectionError: ' + str(e), doi_url="https://doi.org/" + link.doi)
            logging_service.logger.error('ConnectionError: ' + str(e))
            #self.store_crossref(link_id, crossref_object)
            """
            self.logging_service.logger.debug(
                f'crossref for search result: {link_id} parsed and stored in database')
            """
        finally:
            self.search_doi_service.to_state(SearchDOICrossrefSearchedState(self.search_doi_service))