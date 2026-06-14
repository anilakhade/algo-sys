import os
import logging
from dotenv import load_dotenv

from brokers.dhan_broker import DhanBroker
from src.margin_calculator import DhanMarginCalculator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Margin_Tester")

def find_option_token(broker, symbol: str, exchange: str, expiry_date: str, strike_price: float, option_type: str) -> str:
    """
    Helper function to safely look up option contract tokens from the broker's instrument storage.
    Adjusts lookup keys based on standard Dhan master file structures.
    """
    logger.info(f"Searching token for {symbol} {expiry_date} {strike_price} {option_type} on {exchange}...")
    
    # Access the underlying database/list loaded in RAM by your broker class
    # Usually stored inside broker._instruments under an underlying list or data frame
    instruments_list = getattr(broker._instruments, 'instruments', []) or getattr(broker._instruments, 'data', [])
    
    # If standard attributes aren't found, try to search via your existing get_token or loop
    for inst in instruments_list:
        # Match core criteria safely
        if inst.get("exchange_segment") == exchange or inst.get("exchange") == exchange:
            # Check symbol matching (e.g., NIFTY, CRUDEOIL)
            inst_sym = inst.get("symbol", "").upper()
            if symbol in inst_sym:
                # Check option type, strike and expiry
                if inst.get("option_type") == option_type and float(inst.get("strike_price", 0)) == float(strike_price):
                    # Check expiry match contains the string (e.g., '2026-06-30' or '30-JUN')
                    if expiry_date.upper() in str(inst.get("expiry_date", "")).upper():
                        return str(inst.get("token", inst.get("securityId")))
                        
    # Fallback/Mock token if contract search needs manual string matching for your specific file schema
    logger.warning(f"Could not automatically resolve exact token id for {symbol}. Using dynamic search fallback.")
    return None

def test_margin_baskets():
    load_dotenv()
    
    print("\n" + "="*80)
    print("                DHAN MULTI-ORDER BASKET MARGIN TESTING GRID")
    print("="*80)

    # 1. Initialize broker to authenticate and load instrument master to RAM
    broker = DhanBroker(
        client_id=os.getenv("DHAN_CLIENT_ID"),
        pin=os.getenv("DHAN_PIN"),
        totp_secret=os.getenv("DHAN_TOTP_SECRET")
    )
    
    session_token = broker.login()
    if not session_token:
        print("[FAIL] Broker login failed. Cannot proceed without an active access-token.")
        return

    # 2. Instantiate the margin calculator with the active session token
    margin_engine = DhanMarginCalculator(
        client_id=os.getenv("DHAN_CLIENT_ID"),
        access_token=session_token
    )

    # 3. Resolve contract tokens (Using dummy fallbacks if exact string forms vary in your local master)
    nifty_ce_token = find_option_token(broker, "NIFTY", "NSE_FNO", "30-JUN", 23500, "CE") or "54231"
    nifty_pe_token = find_option_token(broker, "NIFTY", "NSE_FNO", "30-JUN", 23500, "PE") or "54232"
    
    crude_ce_token = find_option_token(broker, "CRUDEOIL", "MCX_FO", "16-JUN", 8000, "CE") or "89431"
    crude_pe_token = find_option_token(broker, "CRUDEOIL", "MCX_FO", "16-JUN", 8000, "PE") or "89432"

    # ------------------------------------------------------------------
    # BASKET 1: NSE NIFTY SHORT STRADDLE (Sell Call + Sell Put)
    # ------------------------------------------------------------------
    print("\n[STRATEGY 1] Assembling NIFTY 23500 Short Straddle Basket...")
    nifty_straddle = [
        {
            "exchange_segment": "NSE_FNO",
            "security_id": nifty_ce_token,
            "direction": "SELL",
            "quantity": 65,  # Standard Nifty lot size
            "product_type": "MARGIN",
            "price": 0.0
        },
        {
            "exchange_segment": "NSE_FNO",
            "security_id": nifty_pe_token,
            "direction": "SELL",
            "quantity": 65,
            "product_type": "MARGIN",
            "price": 0.0
        }
    ]
    
    nifty_res = margin_engine.calculate_basket_margin(nifty_straddle)
    if nifty_res["status"] == "success":
        print(f"  [PASS] NIFTY Straddle Margin Calculated:")
        print(f"         Total Combined Margin : Rs. {nifty_res['total_margin']:,.2f}")
        print(f"         SPAN Component        : Rs. {nifty_res['span_margin']:,.2f}")
        print(f"         Exposure Component    : Rs. {nifty_res['exposure_margin']:,.2f}")
    else:
        print(f"  [FAIL] NIFTY Margin Request Rejected: {nifty_res.get('message')}")

    # ------------------------------------------------------------------
    # BASKET 2: MCX CRUDEOIL SHORT STRADDLE (Sell Call + Sell Put)
    # ------------------------------------------------------------------
    print("\n[STRATEGY 2] Assembling MCX CRUDEOIL 8000 Short Straddle Basket...")
    crude_straddle = [
        {
            "exchange_segment": "MCX_FO",
            "security_id": crude_ce_token,
            "direction": "SELL",
            "quantity": 10,  # Standard Crude Oil lot size
            "product_type": "MARGIN",
            "price": 0.0
        },
        {
            "exchange_segment": "MCX_FO",
            "security_id": crude_pe_token,
            "direction": "SELL",
            "quantity": 10,
            "product_type": "MARGIN",
            "price": 0.0
        }
    ]

    crude_res = margin_engine.calculate_basket_margin(crude_straddle)
    if crude_res["status"] == "success":
        print(f"  [PASS] CRUDEOIL Straddle Margin Calculated:")
        print(f"         Total Combined Margin : Rs. {crude_res['total_margin']:,.2f}")
        print(f"         SPAN Component        : Rs. {crude_res['span_margin']:,.2f}")
        print(f"         Exposure Component    : Rs. {crude_res['exposure_margin']:,.2f}")
    else:
        print(f"  [FAIL] MCX CRUDEOIL Margin Request Rejected: {crude_res.get('message')}")

    print("\n" + "="*80)
    print("                        DIAGNOSTIC RUN COMPLETE")
    print("="*80 + "\n")
    
    broker.logout()

if __name__ == "__main__":
    test_margin_baskets()