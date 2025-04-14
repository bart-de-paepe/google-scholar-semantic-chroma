from abc import ABC  # Abstract Base Class
from datetime import datetime, timezone

class Entity(ABC):
    def __init__(self):
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def get_created_at_formatted(self):
        return self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_updated_at_formatted(self):
        return self.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    