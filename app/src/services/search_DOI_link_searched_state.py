from time import sleep

from requests_toolbelt.utils import dump

from app.src.services.search_DOI_content_searched_state import SearchDOIContentSearchedState
from app.src.services.search_DOI_state import SearchDOIState
from app.src.shared.helper import do_external_request, search_in_text, search_in_pdf


class SearchDOILinkedSearchedState(SearchDOIState):
    def __init__(self, search_doi_service):
        super().__init__(search_doi_service)

    def to_string(self):
        return "link searched"

    def search_content(self, link, media_type, logging_service):
        sleep(5) # wait 5 seconds to avoid sending too many requests
        response = link.do_request(logging_service)
        link.response_code = response.status_code
        logging_service.logger.debug(f"Response code for online resource: {response.status_code}")
        if response.status_code == 200:
            header = response.headers
            content_type = header.get('content-type')
            link.response_type = content_type
            if link.check_accepted_type_html() or link.check_accepted_type_pdf():
                link.log_message = "DOI not found"
                match link.response_type:
                    case 'text/html':
                        # logging the entire response for debugging purposes
                        """
                        response_data = dump.dump_all(response)
                        self.logging_service.logger.debug(response_data.decode())
                        """
                        logging_service.logger.debug("text/html")
                        html = response.text
                        #logging_service.logger.debug("******************")
                        #logging_service.logger.debug(html)
                        #logging_service.logger.debug("******************")
                        search_in_text(html, link)
                    case 'application/pdf':
                        # ToDo media_type isn't used yet, don't know if we can do something smart with it..
                        logging_service.logger.debug("application/pdf")
                        pdf = response.content
                        search_in_pdf(pdf, link)
            else:
                link.is_accepted_type = False
                link.log_message = "Response type not supported"
                logging_service.logger.debug("Response type not supported for online resource")

        else:
            link.log_message = "Bad status code"
            logging_service.logger.debug("Bad status code for online resource")

        if link.doi:
            logging_service.logger.debug("DOI found in content")
        self.search_doi_service.to_state(SearchDOIContentSearchedState(self.search_doi_service))