import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
DATABASE = os.getenv('DATABASE')
COLLECTION_EMAILS = os.getenv('COLLECTION_EMAILS')
COLLECTION_SEARCH_RESULTS = os.getenv('COLLECTION_SEARCH_RESULTS')
COLLECTION_CROSSREF = os.getenv('COLLECTION_CROSSREF')

class DBService:
    def __init__(self, client: MongoClient):
        self.client = client
        self.db = self.client[DATABASE]
        self.collection = self.db[COLLECTION_EMAILS]

    def set_collection(self, collection):
        match collection:
            case 'emails':
                self.collection = self.db[COLLECTION_EMAILS]
            case 'search_results':
                self.collection = self.db[COLLECTION_SEARCH_RESULTS]
            case 'crossref':
                self.collection = self.db[COLLECTION_CROSSREF]

    def insert_one(self, document):
        document_id = self.collection.insert_one(document).inserted_id
        return document_id

    def select_one(self, document_id):
        document = self.collection.find_one({'_id': document_id})
        return document

    def select_what_where(self, what, where):
        result = self.collection.find(where, what)
        return result

    def update_one_what_where(self, what, where):
        for k, v in what.items():
            result = self.collection.update_one(where, {'$set': {k: v}})


