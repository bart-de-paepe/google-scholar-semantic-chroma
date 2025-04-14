import os
from pathlib import Path

from selenium import webdriver

from app.src.services.search_DOI_embedded_searched_state import SearchDOIEmbeddedSearchedState
from app.src.services.search_DOI_state import SearchDOIState
from app.src.shared.helper import search_in_pdf_file


class SearchDOIContentSearchedState(SearchDOIState):
    def __init__(self, search_doi_service):
        super().__init__(search_doi_service)

    def to_string(self):
        return "content searched"

    def search_embedded(self, link, logging_service):
        url = link.location_replace_url

        options = webdriver.ChromeOptions()

        download_folder = os.path.join(str(Path(__file__).parent.parent.parent.parent), "online_pdf")

        logging_service.logger.debug(f"Download folder: {download_folder}")

        profile = {
            "plugins.plugins_list": [{"enabled": False, "name": "Chrome PDF Viewer"}],
            "download.default_directory": download_folder,
            "download.extensions_to_open": "",
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        options.add_experimental_option("prefs", profile)
        options.add_argument("start-maximized") # open Browser in maximized mode
        options.add_argument("disable-infobars") # disabling infobars
        options.add_argument("--disable-extensions") # disabling extensions
        options.add_argument("--disable-gpu") # applicable to windows os only
        options.add_argument("--disable-dev-shm-usage") # overcome limited resource problems
        options.add_argument("--no-sandbox") # Bypass OS security  model
        options.add_argument("--headless")

        logging_service.logger.debug("Downloading file from link: {}".format(link.location_replace_url))
        print("Downloading file from link: {}".format(link.location_replace_url))

        driver = webdriver.Chrome(options=options)
        driver.get(url)

        logging_service.logger.debug("Status: Download Complete.")
        print("Status: Download Complete.")

        driver.close()

        link.log_message = "pdf downloaded"

        for f in os.listdir(download_folder):
            search_in_pdf_file(os.path.join(download_folder, f), link)
            os.remove(os.path.join(download_folder, f))

        if link.doi:
            logging_service.logger.debug("DOI found in embedded")


        self.search_doi_service.to_state(SearchDOIEmbeddedSearchedState(self.search_doi_service))