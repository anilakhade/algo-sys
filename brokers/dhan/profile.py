import logging

logger = logging.getLogger(__name__)

class DhanProfile:
    def __init__(self, auth_provider):
        self.auth = auth_provider
        self.logger = logger

    def get(self) -> dict:
        return {
            "clientName": f"Dhan Client {self.auth.client_id}",
            "status": "ACTIVE"
        }