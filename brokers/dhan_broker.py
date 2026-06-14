import logging
from brokers.base import BaseBroker

from brokers.dhan.login import DhanAuth
from brokers.dhan.profile import DhanProfile
from brokers.dhan.instruments import DhanInstruments
from brokers.dhan.websocket import DhanWebSocket
from brokers.dhan.margin import DhanMargin
from brokers.dhan.orders import DhanOrders
from brokers.dhan.portfolio import DhanPortfolio

logger = logging.getLogger(__name__)

class DhanBroker(BaseBroker):
    
    def __init__(self, client_id: str, pin: str, totp_secret: str):
        self.logger = logger
        self._login = DhanAuth(client_id=client_id, pin=pin, totp_secret=totp_secret)

        self._profile = DhanProfile(auth_provider=self._login)
        self._instruments = DhanInstruments(auth_provider=self._login)
        self._websocket = DhanWebSocket(auth_provider=self._login)
        self._margin = DhanMargin(auth_provider=self._login)
        self._orders = DhanOrders(auth_provider=self._login)
        self._portfolio = DhanPortfolio(auth_provider=self._login)
                
    def login(self) -> str:
        self.logger.info("Dhan Broker Initiating master pipeline authentication...")
        session_token = self._login.execute()

        if session_token:
            self.logger.info("Authentication verified. Synchronizing network IP security matrix...")
            try:
                self._login.sync_current_ip()
            except Exception as ip_err:
                self.logger.warning(f"Automated IP gateway sync bypassed or deferred: {ip_err}")

            self.logger.info("Loading Instrument Master...")
            try:
                self._instruments.download()
                self.logger.info("Instrument master downloaded and indexed successfully in RAM.")
            except Exception as e:
                self.logger.error(f"Critical System Alert: Broker logged in, but Instrument Master failed to load: {e}")

        return session_token

    def get_profile(self) -> dict:
        return self._profile.get()

    def get_instruments(self):
        return self._instruments.download()

    def start_market_websocket(self, instruments_list: list, on_tick_callback):
        return self._websocket.start_market(instruments_list, on_tick_callback)

    def start_order_websocket(self, on_order_callback):
        return self._websocket.start_order(on_order_callback)

    def get_margin(self) -> dict:
        return self._margin.get()

    def get_positions(self) -> list:
        return self._portfolio.get_positions()

    def get_holdings(self) -> list:
        return self._portfolio.get_holdings()

    def place_order(self, order_packet) -> dict:
        return self._orders.place(order_packet)

    def modify_order(self, order_id: str, order_packet: dict) -> dict:
        return self._orders.modify(order_id, order_packet)

    def cancel_order(self, order_id: str) -> dict:
        return self._orders.cancel(order_id)

    def logout(self) -> bool:
        self.logger.info("DhanBroker clearing master session handles...")
        return self._login.logout()