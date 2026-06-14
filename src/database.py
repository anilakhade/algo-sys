import os
import logging
from typing import Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class PaperDatabase:
    def __init__(self):
        self.url: str = os.getenv("SUPABASE_URL", "")
        self.key: str = os.getenv("SUPABASE_KEY", "")
        self.logger = logger
        
        if not self.url or not self.key:
            self.logger.error("Supabase environment configuration parameters missing inside active environment matrix.")
            self.client: Optional[Client] = None
        else:
            self.client = create_client(self.url, self.key)

    def create_paper_account(self, account_id: str, account_name: str, initial_cash: float) -> dict:
        if not self.client: return {"status": "error", "message": "No DB client"}
        try:
            payload = {
                "account_id": str(account_id),
                "account_name": str(account_name),
                "initial_cash": float(initial_cash),
                "current_cash": float(initial_cash),
                "available_margin": float(initial_cash),
                "utilized_margin": 0.00,
                "is_active": True
            }
            res = self.client.table("paper_accounts").upsert(payload).execute()
            return {"status": "success", "data": res.data}
        except Exception as e:
            self.logger.error(f"Failed to provision paper account record '{account_id}': {e}")
            return {"status": "error", "message": str(e)}

    def create_strategy_instance(self, strategy_id: str, account_id: str, name: str, strat_type: str, capital: float) -> dict:
        if not self.client: return {"status": "error", "message": "No DB client"}
        try:
            payload = {
                "strategy_id": str(strategy_id),
                "account_id": str(account_id),
                "strategy_name": str(name),
                "strategy_type": str(strat_type),
                "allocated_capital": float(capital),
                "current_pnl": 0.00,
                "is_running": True
            }
            res = self.client.table("strategies").upsert(payload).execute()
            return {"status": "success", "data": res.data}
        except Exception as e:
            self.logger.error(f"Failed to register strategy module instance '{strategy_id}': {e}")
            return {"status": "error", "message": str(e)}

    def get_account_state(self, account_id: str) -> Optional[dict]:
        if not self.client: return None
        try:
            res = self.client.table("paper_accounts").select("*").eq("account_id", account_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            self.logger.error(f"Failed to pull profile metrics state for account '{account_id}': {e}")
            return None

    def update_account_margins(self, account_id: str, cash: float, avail_margin: float, utilized: float) -> bool:
        if not self.client: return False
        try:
            payload = {
                "current_cash": float(cash),
                "available_margin": float(avail_margin),
                "utilized_margin": float(utilized)
            }
            self.client.table("paper_accounts").update(payload).eq("account_id", account_id).execute()
            return True
        except Exception as e:
            self.logger.error(f"Failed to adjust ledger balances on account '{account_id}': {e}")
            return False

    def record_virtual_trade(self, strategy_id: str, account_id: str, packet: dict, price: float, slippage: float, brokerage: float) -> bool:
        if not self.client: return False
        try:
            payload = {
                "strategy_id": str(strategy_id),
                "account_id": str(account_id),
                "security_id": str(packet.get("token")),
                "trading_symbol": str(packet.get("symbol", "UNKNOWN")),
                "exchange": str(packet.get("exchange", "NSE")),
                "direction": str(packet.get("direction", "BUY")),
                "quantity": int(packet.get("quantity", 1)),
                "execution_price": float(price),
                "slippage_cost": float(slippage),
                "brokerage_simulated": float(brokerage)
            }
            self.client.table("virtual_trades").insert(payload).execute()
            return True
        except Exception as e:
            self.logger.error(f"Failed to append immutable trade log item for strategy '{strategy_id}': {e}")
            return False

    def sync_virtual_position(self, strategy_id: str, account_id: str, packet: dict, price: float) -> dict:
        if not self.client: return {"status": "error"}
        try:
            sec_id = str(packet.get("token"))
            direction = str(packet.get("direction", "BUY")).upper()
            exec_qty = int(packet.get("quantity", 1))
            
            # Read existing position block if present
            existing = self.client.table("virtual_positions").select("*")\
                .eq("strategy_id", strategy_id).eq("security_id", sec_id).execute()
            
            qty_modifier = exec_qty if direction == "BUY" else -exec_qty
            
            if not existing.data:
                # Fresh positioning block
                payload = {
                    "strategy_id": strategy_id,
                    "account_id": account_id,
                    "security_id": sec_id,
                    "trading_symbol": str(packet.get("symbol", "UNKNOWN")),
                    "exchange": str(packet.get("exchange", "NSE")),
                    "net_qty": qty_modifier,
                    "average_entry_price": float(price),
                    "realized_pnl": 0.00,
                    "unrealized_pnl": 0.00
                }
                res = self.client.table("virtual_positions").insert(payload).execute()
                return {"status": "created", "data": res.data}
            
            # Position accumulation/reduction calculations
            pos = existing.data[0]
            current_qty = int(pos["net_qty"])
            current_avg = float(pos["average_entry_price"])
            current_realized = float(pos["realized_pnl"])
            
            new_qty = current_qty + qty_modifier
            new_avg = current_avg
            realized_delta = 0.00
            
            if new_qty == 0:
                # Fully liquidated position flatline
                if current_qty > 0:
                    realized_delta = (price - current_avg) * current_qty
                else:
                    realized_delta = (current_avg - price) * abs(current_qty)
                new_avg = 0.00
            elif (current_qty > 0 and qty_modifier > 0) or (current_qty < 0 and qty_modifier < 0):
                # Escalating scaling entries (Averages weighted upwards/downwards)
                total_cost = (current_avg * abs(current_qty)) + (price * exec_qty)
                new_avg = total_cost / abs(new_qty)
            else:
                # Trimming positions (Partial distribution profit captures)
                trimmed_qty = min(abs(current_qty), exec_qty)
                if current_qty > 0:
                    realized_delta = (price - current_avg) * trimmed_qty
                else:
                    realized_delta = (current_avg - price) * trimmed_qty
            
            payload = {
                "net_qty": new_qty,
                "average_entry_price": new_avg,
                "realized_pnl": current_realized + realized_delta,
                "updated_at": "now()"
            }
            
            res = self.client.table("virtual_positions").update(payload)\
                .eq("strategy_id", strategy_id).eq("security_id", sec_id).execute()
                
            return {"status": "updated", "data": res.data}
        except Exception as e:
            self.logger.error(f"Failed handling positional processing matrix rules: {e}")
            return {"status": "error", "message": str(e)}

    def load_all_active_positions(self) -> list:
        if not self.client: return []
        try:
            res = self.client.table("virtual_positions").select("*").neq("net_qty", 0).execute()
            return res.data if res.data else []
        except Exception as e:
            self.logger.error(f"Failed fetching globally active database inventory lines: {e}")
            return []