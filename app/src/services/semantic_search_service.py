import os

from app.src.domain.link import Link
from app.src.services.db_service import DBService
from app.src.services.logging_service import LoggingService

import chromadb
import requests

from dotenv import load_dotenv
load_dotenv()
IMIS = os.getenv('IMIS')

class SemanticSearchService:
    def __init__(self, db_service: DBService, logging_service: LoggingService):
        self.db_service = db_service
        self.logging_service = logging_service
        chroma_client = chromadb.Client()
        # https://docs.trychroma.com/docs/collections/configure
        self.collection = chroma_client.create_collection(
            name="my_collection",
            metadata={
                "hnsw:space": "cosine"
            }
        )

        self.initialize_embeddings()


    def initialize_embeddings(self):
        result = requests.get(IMIS)
        publications = result.json()
        documents = []
        ids = []
        count = 1
        for publication in publications:
            #self.logging_service.logger.debug(publication)
            documents.append(publication['StandardTitle'])
            ids.append(f"id{count}")
            count+=1

        self.collection.add(
            documents=documents,
            ids=ids
        )

    def get_unprocessed_ids(self):
        where = {"link.is_DOI_success": False, "link.is_processed": False}
        what = {"_id": 1}
        self.db_service.set_collection("search_results")
        unprocessed_ids = self.db_service.select_what_where(what, where)
        return unprocessed_ids

    def get_current_link(self, search_result_id):
        self.db_service.set_collection("search_results")
        result = self.db_service.select_one(search_result_id)
        current_link = Link(result["link"]["url"], result["link"]["location_replace_url"], result["link"]["response_code"], result["link"]["response_type"], result["link"]["is_accepted_type"], result["link"]["DOI"], result["link"]["log_message"], result["link"]["is_DOI_success"], result["link"]["is_processed"])
        return current_link

    def get_title(self, search_result_id):
        where = {"_id": search_result_id}
        what = {"title": 1, "_id": 0}
        self.db_service.set_collection("search_results")
        title_cursor = self.db_service.select_what_where(what, where)
        title = title_cursor.next()
        title_cursor.close()
        return title['title']

    def do_semantic_search(self, title):
        results = self.collection.query(
            query_texts=[title],  # Chroma will embed this for you
            n_results=2  # how many results to return
        )
        score = self.convert_distance_to_score(results['distances'][0][0])
        return score

    def convert_distance_to_score(self, distance):
        score = distance
        return score