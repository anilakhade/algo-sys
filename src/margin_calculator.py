import os
import logging
import httpx
from typing import List, Dict, Optional

logger = logging.getLogger("Margin_Calculator")

class DhanMarginCalculator:
    def __init__(self, client_id: Optional[str] = None, access_token: Optional[str] = None):
        # Fall back to environment variables if parameters are not explicitly provided
        self.client_id = client_id or os.getenv("DHAN_CLIENT_ID", "")
        self.access_token = access_token or os.getenv("DHAN_ACCESS_TOKEN", "")
        
        # Dhan Production V2 API multi-order margin endpoint
        self.url = "https://api.dhan.co/v2/margincalculator/multi"
        self.logger = logger

    def _normalize_leg_structure(self, raw_leg: dict) -> dict:
        """
        Standardizes user input formats to match the exact JSON keys 
        required by the Dhan API schema seen in image_1d5dda.jpg.
        """
        # Map product types to official Dhan uppercase enums
        prod = str(raw_leg.get("product_type", raw_leg.get("productType", "MARGIN"))).upper()
        if prod in ["MIS", "INTRA", "INTRADAY"]:
            prod = "INTRADAY"
        elif prod in ["CNC", "DELIVERY"]:
            prod = "CNC"
        elif prod in ["NRML", "MARGIN", "MTF"]:
            prod = "MARGIN"
            
        return {
            "exchangeSegment": str(raw_leg.get("exchange_segment", raw_leg.get("exchangeSegment", "NSE_FNO"))).upper(),
            "transactionType": str(raw_leg.get("direction", raw_leg.get("transactionType", "BUY"))).upper(),
            "quantity": int(raw_leg.get("quantity", 1)),
            "productType": prod,
            "securityId": str(raw_leg.get("security_id", raw_leg.get("securityId", ""))),
            "price": float(raw_leg.get("price", 0.0)),
            "triggerPrice": float(raw_leg.get("trigger_price", raw_leg.get("triggerPrice", 0.0)))
        }

    def calculate_basket_margin(self, strategy_legs: List[Dict], include_position: bool = False, include_orders: bool = False) -> dict:
        """
        Sends a complete basket of legs to Dhan to retrieve the combined 
        hedged margin requirement using SPAN and Exposure offset algorithms.
        """
        if not self.access_token or not self.client_id:
            return {"status": "error", "message": "Missing Dhan API authentication credentials."}

        if not strategy_legs:
            return {"status": "error", "message": "Cannot calculate margin for an empty basket."}

        # 1. Map user legs into the verified API inner structure
        normalized_scrips = [self._normalize_leg_structure(leg) for leg in strategy_legs]

        # 2. Construct the outer request body payload matching the Dhan specification exactly
        payload = {
            "dhanClientId": self.client_id,
            "includePosition": include_position,
            "includeOrder": include_orders,  # Explicitly singular 'includeOrder'
            "scripList": normalized_scrips    # Explicitly camelCase 'scripList' 
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "access-token": self.access_token
        }

        try:
            # 3. Fire synchronous HTTP POST call to Dhan's margin engine
            with httpx.Client(timeout=10.0) as client:
                response = client.post(self.url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "total_margin": float(data.get("totalMargin", 0.0)),
                    "span_margin": float(data.get("spanMargin", 0.0)),
                    "exposure_margin": float(data.get("exposure", data.get("exposureMargin", 0.0))),
                    "raw_response": data
                }
            else:
                # Catch API rejections or parameter mismatch warnings directly
                return {
                    "status": "rejected",
                    "http_code": response.status_code,
                    "message": response.text
                }

        except Exception as e:
            self.logger.error(f"Failed execution request on Dhan Margin network link: {e}")
            return {"status": "error", "message": str(e)}