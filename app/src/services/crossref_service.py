import json
import re

import crossref_commons.retrieval
from bson import ObjectId

from app.src.domain.crossref import Crossref
from app.src.domain.link import Link
from app.src.services.db_service import DBService
from app.src.services.logging_service import LoggingService


class CrossrefService:
    def __init__(self, db_service: DBService, logging_service: LoggingService):
        self.db_service = db_service
        self.logging_service = logging_service

    # query all the unprocessed _id's
    def get_unprocessed_ids(self):
        where = {"link.is_DOI_success": True, "link.is_processed": False}
        what = {"_id": 1}
        self.db_service.set_collection("search_results")
        unprocessed_ids = self.db_service.select_what_where(what, where)
        return unprocessed_ids

    # for every _id get the corresponding document link
    def get_link(self, link_id):
        where = {"_id": link_id}
        what = {"link": 1, "_id": 0}
        self.db_service.set_collection("search_results")
        link_cursor = self.db_service.select_what_where(what, where)
        link = link_cursor.next()
        link_object = Link(url=link['link']['url'], location_replace_url=link['link']['location_replace_url'],
                           response_code=link['link']['response_code'], response_type=link['link']['response_type'],
                           is_accepted_type=link['link']['is_accepted_type'], doi=link['link']['DOI'],
                           log_message=link['link']['log_message'], is_doi_success=link['link']['is_DOI_success'],
                           is_processed=link['link']['is_processed'])
        self.logging_service.logger.debug(link_object.location_replace_url)
        link_cursor.close()
        return link_object

    def get_crossref(self, link_id, link):
        try:
            response = crossref_commons.retrieval.get_publication_as_json(link.doi)
            #self.logging_service.logger.debug(json.dumps(response))
            #title
            title = response.get('title')
            if title is not None:
                title = title[0]
                self.logging_service.logger.debug('title: ' + title)
            else:
                self.logging_service.logger.debug('title is None')
            #author
            all_author_string = ''
            author = response.get('author')
            if author is not None:
                for current_author in author:
                    given = current_author.get('given')
                    family = current_author.get('family')
                    author_string = f"{given} {family}, "
                    all_author_string += author_string
            all_author_string = all_author_string.rstrip(", ")
            self.logging_service.logger.debug('author: ' + all_author_string)
            #year
            year = response.get('published')
            if year is not None:
                year = year.get('date-parts')
                year = year[0]
                year = year[0]
                year = int(year)
                self.logging_service.logger.debug('year: ' + str(year))
            else:
                self.logging_service.logger.debug('year is None')
            #publisher
            publisher = response.get('publisher')
            if publisher is not None:
                self.logging_service.logger.debug('publisher: ' + publisher)
            else:
                self.logging_service.logger.debug('publisher is None')
            log_message = "Crossref retrieved successfully."
            crossref_object = Crossref(200, True, title, all_author_string, year, publisher, log_message, "https://doi.org/" + link.doi)
            self.store_crossref(link_id, crossref_object)
        except ValueError as e:
            crossref_object = Crossref(response_code=404, log_message='ValueError: ' + str(e), doi_url="https://doi.org/" + link.doi)
            self.logging_service.logger.error('ValueError: ' + str(e))
            self.store_crossref(link_id, crossref_object)
        except ConnectionError as e:
            all_numbers = re.findall(r'\d+', str(e))
            crossref_object = Crossref(response_code=all_numbers[0], log_message='ConnectionError: ' + str(e), doi_url="https://doi.org/" + link.doi)
            self.logging_service.logger.error('ConnectionError: ' + str(e))
            self.store_crossref(link_id, crossref_object)
            self.logging_service.logger.debug(
                f'crossref for search result: {link_id} parsed and stored in database')

    def store_crossref(self, link_id, crossref: Crossref):
        post = {
                "created_at": crossref.get_created_at_formatted(),
                "updated_at": crossref.get_updated_at_formatted(),
                "search_result": ObjectId(link_id),
                "title": crossref.title,
                "author": crossref.author,
                "publisher": crossref.publisher,
                "year": crossref.year,
                "doi_url": crossref.doi_url,
                "api_url": crossref.api_url,
                "log_message": crossref.log_message,
            }
        self.db_service.set_collection("crossref")
        post_id = self.db_service.insert_one(post)