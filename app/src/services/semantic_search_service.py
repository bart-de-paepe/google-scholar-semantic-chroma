from app.src.services.db_service import DBService
from app.src.services.logging_service import LoggingService


class SemanticSearchService:
    def __init__(self, db_service: DBService, logging_service: LoggingService):
        self.db_service = db_service
        self.logging_service = logging_service

    def get_unprocessed_ids(self):
        pass