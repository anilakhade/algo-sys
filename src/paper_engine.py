import logging
import random
from typing import Dict, List, Callable, Optional
from src.database import PaperDatabase

logger = logging.getLogger(__name__)

class PaperEngine:
    def __init__(self, db_client: PaperDatabase):
        self.db = db_client
        self.logger = logger
        self.routing_table: Dict[str, List[Callable]] = {}
        self.active_positions_cache: List[dict] = []
        self.refresh_positions_cache()

    def refresh_positions_cache(self):
        """Pulls updated active open inventory balances from the cloud database layer."""
        self.active_positions_cache = self.db.load_all_active_positions()

    def register_live_subscription(self, security_id: str, callback: Callable):
        """Maps an individual strategy's callback wrapper to a specific streaming ticker symbol."""
        sec_id = str(security_id)
        if sec_id not in self.routing_table:
            self.routing_table[sec_id] = []
        if callback not in self.routing_table[sec_id]:
            self.routing_table[sec_id].append(callback)

    def handle_market_tick(self, tick_packet: dict):
        """
        Processes streaming websocket prices. 
        Updates running unrealized PnL matrices across all portfolios and dispatches ticks.
        """
        sec_id = str(tick_packet.get("security_id"))
        ltp = float(tick_packet.get("LTP", 0.0))
        if ltp <= 0.0: 
            return

        # 1. Update Floating Mark-to-Market (MTM) profiles for active positions
        for pos in self.active_positions_cache:
            if str(pos.get("security_id")) == sec_id:
                net_qty = int(pos.get("net_qty", 0))
                avg_price = float(pos.get("average_entry_price", 0.0))
                
                if net_qty > 0:
                    unrealized = (ltp - avg_price) * net_qty
                else:
                    unrealized = (avg_price - ltp) * abs(net_qty)
                
                try:
                    self.db.client.table("virtual_positions")\
                        .update({"unrealized_pnl": unrealized})\
                        .eq("position_id", pos["position_id"]).execute()
                except Exception as db_err:
                    self.logger.debug(f"MTM flush deferred for position entry {pos.get('position_id')}: {db_err}")

        # 2. Distribute pricing feed downstream to registered algorithmic strategy engines
        if sec_id in self.routing_table:
            for callback in self.routing_table[sec_id]:
                try:
                    callback(tick_packet)
                except Exception as e:
                    self.logger.error(f"Strategy runtime callback execution fault on Token {sec_id}: {e}")

    def simulate_book_sweep(self, target_qty: int, current_price: float, direction: str, market_depth_packet: Optional[dict] = None) -> float:
        """
        Simulates order flow sweeping across an asset's order book.
        Uses real 5-level websocket depth frames, falling back to a synthetic matrix if missing.
        Applies a compounding tail-end price penalty if the trade size overflows available levels.
        """
        book_layers = None
        if market_depth_packet:
            book_layers = market_depth_packet.get("asks" if direction == "BUY" else "bids")
        
        # Fallback: Build a realistic synthetic 5-level depth map if live feed packets are thin
        if not book_layers:
            book_layers = []
            tick_size = 0.05
            running_price = current_price
            for _ in range(1, 6):
                if direction == "BUY":
                    running_price += tick_size * random.randint(1, 3)
                else:
                    running_price -= tick_size * random.randint(1, 3)
                book_layers.append({
                    "price": round(running_price, 2),
                    "quantity": random.randint(200, 1500)
                })

        remaining_qty = target_qty
        total_value = 0.0
        final_level_price = current_price
        
        for level in book_layers:
            level_qty = int(level["quantity"])
            level_price = float(level["price"])
            final_level_price = level_price
            
            taken_qty = min(remaining_qty, level_qty)
            total_value += taken_qty * level_price
            remaining_qty -= taken_qty
            
            if remaining_qty <= 0:
                break
                
        # OVERFLOW VALVE: Compute structural decay penalties if volume breaches visible rows
        if remaining_qty > 0:
            penalty_pct = 1.0 + (0.001 * (remaining_qty / 1000.0))
            if direction == "BUY":
                adjusted_outer_price = final_level_price * penalty_pct
            else:
                adjusted_outer_price = final_level_price * (2.0 - penalty_pct)
            total_value += remaining_qty * adjusted_outer_price
            
        return round(total_value / target_qty, 2)

    def place_virtual_order(self, account_id: str, strategy_id: str, order_packet: dict) -> dict:
        """
        Validates account risk parameters, locks simulated leverage margins, 
        calculates sweep fills, and appends the final allocations to Supabase.
        """
        account_state = self.db.get_account_state(account_id)
        if not account_state or not account_state.get("is_active"):
            return {"status": "rejected", "remarks": "Account container non-existent or deactivated"}

        current_cash = float(account_state["current_cash"])
        avail_margin = float(account_state["available_margin"])
        utilized_margin = float(account_state["utilized_margin"])

        declared_price = float(order_packet.get("price", 0.0))
        if declared_price <= 0.0:
            return {"status": "rejected", "remarks": "Invalid limit pricing values"}

        qty = int(order_packet.get("quantity", 1))
        prod_type = str(order_packet.get("product_type", "INTRA")).upper()
        direction = str(order_packet.get("direction", "BUY")).upper()

        # Enforce regulatory intraday (MIS: 5x leverage) vs delivery (CNC: 1x leverage) rules
        margin_leverage_factor = 0.20 if prod_type in ["MIS", "INTRA", "INTRADAY"] else 1.00
        
        # Calculate true volume-weighted fill costs using the matching engine sweep
        execution_price = self.simulate_book_sweep(
            target_qty=qty,
            current_price=declared_price,
            direction=direction,
            market_depth_packet=order_packet.get("market_depth_packet")
        )
        
        gross_trade_value = execution_price * qty
        margin_required = gross_trade_value * margin_leverage_factor

        # Pre-Trade Risk Management System (RMS) Firewall Check
        if direction == "BUY" and margin_required > avail_margin:
            return {
                "status": "rejected", 
                "remarks": f"Insufficient margin. Required: {margin_required:.2f}, Available: {avail_margin:.2f}"
            }

        simulated_brokerage = 20.00 # Flat standard Indian execution contract fee
        slippage_cost = abs(execution_price - declared_price) * qty

        # Compute post-trade sub-ledger metrics balances
        if direction == "BUY":
            new_cash = current_cash - gross_trade_value - simulated_brokerage
            new_utilized = utilized_margin + margin_required
        else:
            new_cash = current_cash + gross_trade_value - simulated_brokerage
            new_utilized = max(0.00, utilized_margin - margin_required)

        new_avail_margin = new_cash - new_utilized

        # Commit new balances to the cloud repository
        db_success = self.db.update_account_margins(account_id, new_cash, new_avail_margin, new_utilized)
        if not db_success:
            return {"status": "error", "remarks": "Transactional database lock fault encountered"}

        # Write trade records and synchronize live positions holding allocations
        self.db.record_virtual_trade(strategy_id, account_id, order_packet, execution_price, slippage_cost, simulated_brokerage)
        self.db.sync_virtual_position(strategy_id, account_id, order_packet, execution_price)
        
        # Reset memory cache arrays to immediately capture updated states
        self.refresh_positions_cache()

        return {
            "status": "success",
            "remarks": "Filled",
            "execution_price": execution_price,
            "margin_locked": margin_required
        }