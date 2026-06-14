import logging

logger = logging.getLogger(__name__)

class DhanMargin:
    def __init__(self, auth_provider):
        self.auth = auth_provider
        self.logger = logger

    def get(self) -> dict:
        client = self.auth.get_client()
        if not client:
            self.logger.error("Margin tracking aborted: Invalid broker session handle.")
            return {"availabelBalance": 0.0, "utilizedAmount": 0.0}

        try:
            funds_data = client.get_fund_limits()
            if not funds_data:
                return {"availabelBalance": 0.0, "utilizedAmount": 0.0}

            if isinstance(funds_data, dict):
                if "data" in funds_data and isinstance(funds_data["data"], dict):
                    return funds_data["data"]
                return funds_data

            return {"availabelBalance": 0.0, "utilizedAmount": 0.0}
        except Exception as e:
            self.logger.error(f"Failed to fetch real-time ledger metrics: {e}")
            return {"availabelBalance": 0.0, "utilizedAmount": 0.0}