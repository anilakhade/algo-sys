import logging
import time
from dhanhq import DhanContext, MarketFeed, OrderUpdate

logger = logging.getLogger(__name__)

class DhanWebSocket:
    def __init__(self, auth_provider):
        self.auth = auth_provider
        self.logger = logger
        self.market_feed = None
        self.order_feed = None

    def start_market(self, instruments_list: list, on_tick_callback):
        self.logger.info(f"Initializing market data stream for {len(instruments_list)} assets...")
        
        # 1. Ensure the session is alive and valid
        client = self.auth.get_client()
        if not client:
            self.logger.error("Market feed connection aborted: Invalid Broker session handle.")
            return
        
        # 2. Build the explicit security context from our auth data store
        context = DhanContext(client_id=self.auth.client_id, access_token=self.auth.access_token)
        
        formatted_subscriptions = []
        for asset in instruments_list:
            segment_str = str(asset.get("segment", "")).upper()
            exchange_str = str(asset.get("exchange", "")).upper()
            token_id = str(asset.get("token", ""))

            if segment_str == "INDEX":
                exchange_segment = "IDX_I"
            elif segment_str in ["OPTIDX", "FUTIDX", "OPTSTK", "FUTSTK"]:
                exchange_segment = "NSE_FNO"
            elif exchange_str == "MCX":
                exchange_segment = "MCX_COMM"
            elif exchange_str == "BSE" and segment_str == "EQUITY":
                exchange_segment = "BSE_EQ"
            else:
                exchange_segment = "NSE_EQ"

            subscription_tuple = (exchange_segment, token_id, MarketFeed.Ticker)
            formatted_subscriptions.append(subscription_tuple)

            self.logger.debug(f"Mapped {asset['trading_symbol']} -> Segment: {exchange_segment}, Token: {token_id}")

        try:
            # 3. Pass the freshly instantiated context object directly into MarketFeed
            self.market_feed = MarketFeed(context, formatted_subscriptions, version="v2")
            self.logger.info("Market Feed interface linked successfully with explicit document mapping.")

            while True:
                self.market_feed.run_forever()
                raw_tick_packet = self.market_feed.get_data()

                if raw_tick_packet:
                    on_tick_callback(raw_tick_packet)
                
                time.sleep(0.001)

        except Exception as pipe_fault:
            self.logger.error(f"Live market stream encountered a runtime system exception: {pipe_fault}")
            raise

    def start_order(self, on_order_callback):
        self.logger.info("Connecting to real-time account order update stream...")

        client = self.auth.get_client()
        if not client:
            self.logger.error("Order feed connection aborted: Invalid broker session handle.")
            return None

        try:
            # Build the explicit security context for the transaction pipe
            context = DhanContext(client_id=self.auth.client_id, access_token=self.auth.access_token)
            self.order_feed = OrderUpdate(context)
            self.logger.info("Order feedback channel established. Monitoring incoming transactions...")

            while True:
                self.order_feed.run_forever()
                raw_order_packet = self.order_feed.get_data()

                if raw_order_packet:
                    on_order_callback(raw_order_packet)

                time.sleep(0.001)
        
        except Exception as order_fault:
            self.logger.error(f"Order state loop encountered a runtime system exception: {order_fault}")
            raise