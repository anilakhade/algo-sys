import logging

logger = logging.getLogger(__name__)

class DhanOrders:
    def __init__(self, auth_provider):
        self.auth = auth_provider
        self.logger = logger
        
        self._segment_map = {
            ("NSE", "EQUITY"): "NSE_EQ",
            ("BSE", "EQUITY"): "BSE_EQ",
            ("BSE", "OPTIDX"): "BSE_FNO",
            ("NSE", "INDEX"): "NSE_EQ",
            ("NSE", "FUTIDX"): "NSE_FNO",
            ("NSE", "OPTIDX"): "NSE_FNO",
            ("NSE", "OPTFUT"): "NSE_FNO",
            ("NSE", "FUTSTK"): "NSE_FNO",
            ("NSE", "OPTSTK"): "NSE_FNO",
            ("MCX", "FUTCOM"): "MCX_COMM",
            ("MCX", "OPTFUT"): "MCX_COMM"
        }

    def place(self, order_packet: dict) -> dict:
        client = self.auth.get_client()
        if not client:
            self.logger.error("Order execution denied: Invalid broker session handle.")
            return {"status": "failure", "remarks": "No active session"}

        try:
            exchange = order_packet.get("exchange", "NSE").upper()
            segment = order_packet.get("segment", "EQUITY").upper()
            dhan_segment = self._segment_map.get((exchange, segment), "NSE_EQ")
            
            raw_order_type = order_packet.get("order_type", "MARKET").upper()
            if raw_order_type in ["SL", "STOP_LOSS"]:
                order_type_str = "STOP_LOSS"
            elif raw_order_type in ["SLM", "STOP_LOSS_MARKET"]:
                order_type_str = "STOP_LOSS_MARKET"
            elif raw_order_type == "LIMIT":
                order_type_str = "LIMIT"
            else:
                order_type_str = "MARKET"
            ord_type = getattr(client, order_type_str, getattr(client, "MARKET", "MARKET"))

            raw_prod_type = order_packet.get("product_type", "INTRADAY").upper()
            if raw_prod_type in ["INTRADAY", "MIS", "INTRA"]:
                prod_type_str = "INTRA"
            elif raw_prod_type in ["CNC", "DELIVERY", "INVESTING"]:
                prod_type_str = "CNC"
            elif raw_prod_type == "MARGIN":
                prod_type_str = "MARGIN"
            else:
                prod_type_str = "INTRA"
            prod_type = getattr(client, prod_type_str, getattr(client, "INTRA", "INTRA"))

            api_payload = {
                "security_id": str(order_packet.get("token")),
                "exchange_segment": dhan_segment,
                "transaction_type": getattr(client, order_packet.get("direction", "BUY").upper(), getattr(client, "BUY", "BUY")),
                "quantity": int(order_packet.get("quantity", 1)),
                "order_type": ord_type,
                "product_type": prod_type,
                "price": float(order_packet.get("price", 0.0)),
                "trigger_price": float(order_packet.get("trigger_price", 0.0)),
                "validity": "DAY"
            }

            self.logger.info(f"Routing live order packet for Token {api_payload['security_id']} using SDK v2.2.0 constants...")
            response = client.place_order(**api_payload)
            
            if isinstance(response, dict):
                if response.get("status") == "success":
                    data_block = response.get("data")
                    order_id = data_block.get("orderId") if isinstance(data_block, dict) else None
                    return {"status": "success", "order_id": order_id}
                remarks = response.get("remarks") or response.get("status")
                return {"status": "failed", "remarks": str(remarks)}
            return {"status": "failed", "remarks": str(response)}

        except Exception as e:
            self.logger.error(f"Critical execution fault encountered inside order engine: {e}")
            return {"status": "error", "remarks": str(e)}

    def modify(self, order_id: str, order_packet: dict) -> dict:
        client = self.auth.get_client()
        if not client:
            self.logger.error("Order modification denied: Invalid broker session handle.")
            return {"status": "failure", "remarks": "No active session"}

        try:
            raw_order_type = order_packet.get("order_type", "MARKET").upper()
            if raw_order_type in ["SL", "STOP_LOSS"]:
                order_type_str = "STOP_LOSS"
            elif raw_order_type in ["SLM", "STOP_LOSS_MARKET"]:
                order_type_str = "STOP_LOSS_MARKET"
            elif raw_order_type == "LIMIT":
                order_type_str = "LIMIT"
            else:
                order_type_str = "MARKET"
            ord_type = getattr(client, order_type_str, getattr(client, "MARKET", "MARKET"))

            api_payload = {
                "order_id": str(order_id),
                "order_type": ord_type,
                "leg_name": str(order_packet.get("leg_name", "")),
                "quantity": int(order_packet.get("quantity", 1)),
                "price": float(order_packet.get("price", 0.0)),
                "trigger_price": float(order_packet.get("trigger_price", 0.0)),
                "disclosed_quantity": int(order_packet.get("disclosed_quantity", 0)),
                "validity": "DAY"
            }

            self.logger.info(f"Routing order modification for Order ID {order_id}...")
            response = client.modify_order(**api_payload)
            
            if isinstance(response, dict):
                if response.get("status") == "success":
                    return {"status": "success", "order_id": order_id}
                remarks = response.get("remarks") or response.get("status")
                return {"status": "failed", "remarks": str(remarks)}
            return {"status": "failed", "remarks": str(response)}

        except Exception as e:
            self.logger.error(f"Critical execution fault encountered inside order modification: {e}")
            return {"status": "error", "remarks": str(e)}

    def cancel(self, order_id: str) -> dict:
        client = self.auth.get_client()
        if not client:
            self.logger.error("Order cancellation denied: Invalid broker session handle.")
            return {"status": "failure", "remarks": "No active session"}

        try:
            self.logger.info(f"Routing order cancellation for Order ID {order_id}...")
            response = client.cancel_order(order_id=str(order_id))
            
            if isinstance(response, dict):
                if response.get("status") == "success":
                    return {"status": "success", "order_id": order_id}
                remarks = response.get("remarks") or response.get("status")
                return {"status": "failed", "remarks": str(remarks)}
            return {"status": "failed", "remarks": str(response)}

        except Exception as e:
            self.logger.error(f"Critical execution fault encountered inside order cancellation: {e}")
            return {"status": "error", "remarks": str(e)}