from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseBroker(ABC):
    """This is the CONTRACT / Rule Book
    Every broker (Dhan, Zerodha, Upstox...) MUST follow these rules"""

    @abstractmethod
    def login(self):
        """Login and get token"""
        pass

    @abstractmethod
    def get_instruments(self):
        """Download full master (NSE + BSE + MCX)"""
        pass

    @abstractmethod
    def start_market_websocket(self, on_tick_callback):
        """Live price data"""
        pass

    @abstractmethod
    def start_order_websocket(self, on_order_callback):
        """Live order status (filled, rejected)"""
        pass

    @abstractmethod
    def place_order(self, order: Dict):
        """Place any order"""
        pass

    @abstractmethod
    def get_margin(self):
        """Get available margin"""
        pass

    @abstractmethod
    def get_positions(self):
        """Get current positions"""
        pass

    @abstractmethod
    def get_profile(self):
        """Account details"""
        pass

    @abstractmethod
    def logout(self):
        """Logout"""
        pass