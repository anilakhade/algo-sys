import logging

logger = logging.getLogger(__name__)

class DhanPortfolio:
    def __init__(self, auth_provider):
        self.auth = auth_provider
        self.logger = logger

    def get_positions(self) -> list:
        client = self.auth.get_client()
        if not client:
            self.logger.error("Positions lookup aborted: Invalid broker session handle.")
            return []

        try:
            res = client.get_positions()
            if isinstance(res, list):
                return res
            if isinstance(res, dict) and "data" in res:
                return res["data"] if isinstance(res["data"], list) else []
            return []
        except Exception as e:
            self.logger.error(f"Failed to fetch open positions portfolio: {e}")
            return []

    def get_holdings(self) -> list:
        client = self.auth.get_client()
        if not client:
            self.logger.error("Holdings lookup aborted: Invalid broker session handle.")
            return []

        try:
            res = client.get_holdings()
            if isinstance(res, list):
                return res
            if isinstance(res, dict) and "data" in res:
                return res["data"] if isinstance(res["data"], list) else []
            return []
        except Exception as e:
            self.logger.error(f"Failed to fetch long-term investment holdings: {e}")
            return []