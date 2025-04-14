import re
from time import sleep

from bs4 import BeautifulSoup

from app.src.services.search_DOI_replaced_state import SearchDOIReplacedState
from app.src.services.search_DOI_state import SearchDOIState
from app.src.shared.helper import do_external_request


class SearchDOIUnprocessedState(SearchDOIState):
    def __init__(self, search_doi_service):
        super().__init__(search_doi_service)

    def to_string(self):
        return "unprocessed"

    def replace(self, link, logging_service):
        url = link.url
        sleep(5)    # wait 5 seconds to avoid sending to many requests to Google
        response = do_external_request(url, True)
        link.response_code = response.status_code
        link.location_replace_url = None

        if response.status_code == 200:
            header = response.headers
            content_type = header.get('content-type')
            link.response_type = content_type
            if link.check_accepted_type_html():
                soup = BeautifulSoup(response.text, "html.parser")
                scripts = soup.find_all('script')
                if (len(scripts) == 0):
                    link.log_message = "no script tag found for search result link."
                    logging_service.logger.debug("no script tag found for search result link.")
                while ((link.location_replace_url is None) and (len(scripts) > 0)):
                    script = scripts.pop()
                    if script.string is not None:
                        js_code = script.string
                        pattern = r"location\.replace\(['\"]([^'\"]+)['\"]\)"
                        match = re.search(pattern, js_code)
                        if match:
                            link.location_replace_url = match.group(1)
                            logging_service.logger.debug(
                                f"Extracted location.replace URL for search result link: {link.location_replace_url}")
                        else:
                            link.log_message = "No location.replace url found for search result link"
                            logging_service.logger.debug("No location.replace url found for search result link")
                    else:
                        link.log_message = "script string is None for search result link"
                        logging_service.logger.debug("script string is None for search result link")
            else:
                link.log_message = "No HTML response for search result link"
                logging_service.logger.debug("No HTML response for search result link")
        else:
            link.log_message = "Bad status code for search result link"
            logging_service.logger.debug("Bad status code for search result link")

        self.search_doi_service.to_state(SearchDOIReplacedState(self.search_doi_service))
