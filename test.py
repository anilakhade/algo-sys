import os
import sys
import logging
import time
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger("Full_Stack_Validator")

try:
    from brokers.dhan_broker import DhanBroker
except ImportError as e:
    logger.error(f"Failed to import DhanBroker orchestrator framework: {e}")
    sys.exit(1)

load_dotenv()

def run_rigorous_infrastructure_diagnostic():
    logger.info("Starting complete end-to-end architectural system diagnostic...")
    
    client_id = os.getenv("DHAN_CLIENT_ID")
    pin = os.getenv("DHAN_PIN")
    totp_secret = os.getenv("DHAN_TOTP_SECRET")

    if not all([client_id, pin, totp_secret]):
        logger.critical("Diagnostic Aborted: Execution credentials missing inside local .env configuration.")
        return

    broker = DhanBroker(client_id=client_id, pin=pin, totp_secret=totp_secret)

    try:
        # ====================================================================
        # TEST PHASE 1: AUTHENTICATION & SECURITY IP SYNCHRONIZATION
        # ====================================================================
        print("\n" + "="*80)
        print(" PHASE 1: TESTING CORE AUTHENTICATION AND GATEWAY SYNC NETWORK SECURITY")
        print("="*80)
        
        session_token = broker.login()
        if not session_token:
            logger.error("Phase 1 Failure: Master handshake login authentication rejected.")
            return
        
        # ====================================================================
        # TEST PHASE 2: HIGH-PERFORMANCE RAM LOOKUPS
        # ====================================================================
        print("\n" + "="*80)
        print(" PHASE 2: TESTING INSTRUMENT DICTIONARY DATA RESOLUTION & GRID SPEED")
        print("="*80)
        
        start_lookup = time.perf_counter()
        asset_sample = broker._instruments.get_token(symbol="RELIANCE", exchange="NSE", instrument="EQUITY")
        end_lookup = time.perf_counter()
        
        if asset_sample:
            logger.info("RAM Map Lookup successful for 'RELIANCE'")
            print(f" -> Target Asset Identifier : Token ID {asset_sample['token']} | Segment: {asset_sample['segment']}")
            print(f" -> Database Search Latency : {(end_lookup - start_lookup) * 1000:.4f} milliseconds")
        else:
            logger.warning("Phase 2 Notice: Memory lookup failed or database index cache is incomplete.")

        # ====================================================================
        # TEST PHASE 3: ACCOUNT TELEMETRY & RISK MARGIN READOUTS
        # ====================================================================
        print("\n" + "="*80)
        print(" PHASE 3: FETCHING ACCOUNT TELEMETRY SPECIFICATIONS & MARGIN LEDGERS")
        print("="*80)
        
        profile = broker.get_profile()
        margin = broker.get_margin()
        
        print(f" -> Registered Trading Client : {profile.get('clientName', 'N/A')}")
        print(f" -> System Operations Status  : {profile.get('status', 'N/A')}")
        print(f" -> Available Trading Capital : INR {margin.get('availabelBalance', 0.0)}")
        print(f" -> Margin Utilized Today     : INR {margin.get('utilizedAmount', 0.0)}")

        # ====================================================================
        # TEST PHASE 4: PORTFOLIO AND OPEN POSITION BALANCES
        # ====================================================================
        print("\n" + "="*80)
        print(" PHASE 4: INSPECTING LIVE TRADE POSITIONS AND LONG-TERM HOLDINGS")
        print("="*80)
        
        open_positions = broker.get_positions()
        investment_holdings = broker.get_holdings()
        
        print(f" -> Active Intraday Positions Extracted: {len(open_positions) if isinstance(open_positions, list) else 0}")
        if isinstance(open_positions, list) and len(open_positions) > 0:
            for idx, pos in enumerate(open_positions[:3], 1):
                print(f"    [{idx}] Sym: {pos.get('tradingSymbol')} | Net Qty: {pos.get('netQty')} | PnL: INR {pos.get('realizedProfit', 0.0)}")
                
        print(f" -> Total Asset Holding Units Extracted : {len(investment_holdings) if isinstance(investment_holdings, list) else 0}")
        if isinstance(investment_holdings, list) and len(investment_holdings) > 0:
            for idx, hold in enumerate(investment_holdings[:3], 1):
                print(f"    [{idx}] Stock: {hold.get('tradingSymbol')} | Total Qty: {hold.get('holdingQty')} | Current Value: INR {hold.get('currentValue', 0.0)}")

        # ====================================================================
        # TEST PHASE 5: ENUM MAPPING AND TRANSLATION LOGIC
        # ====================================================================
        print("\n" + "="*80)
        print(" PHASE 5: TESTING SHORT-HAND MAPPING TRANSLATION AND ORDER PLACEMENT")
        print("="*80)
        
        target_asset = broker._instruments.get_token(symbol="TATASTEEL", exchange="NSE", instrument="EQUITY")
        if target_asset:
            test_order_packet = {
                "token": target_asset["token"],
                "exchange": target_asset["exchange"],
                "segment": target_asset["segment"],
                "direction": "BUY",
                "quantity": 1,
                "order_type": "SL",      
                "product_type": "MIS",   
                "price": 160.00,
                "trigger_price": 159.50
            }
            
            logger.info("Executing Sub-Test A: Order Placement Pipeline...")
            place_res = broker.place_order(test_order_packet)
            print(f"   -> Placement Response: {place_res}")

            logger.info("Executing Sub-Test B: Order Modification Pipeline (Simulating Mock ID)...")
            mod_res = broker.modify_order("999999999999", test_order_packet)
            print(f"   -> Modification Response: {mod_res}")

            logger.info("Executing Sub-Test C: Order Cancellation Pipeline (Simulating Mock ID)...")
            cancel_res = broker.cancel_order("999999999999")
            print(f"   -> Cancellation Response: {cancel_res}")
        else:
            logger.error("Phase 5 Failure: Could not extract token ID mapping metadata for order testing.")

        # ====================================================================
        # TEST PHASE 6: STREAMING DATA FEED WEBSOCKET CHANNELS
        # ====================================================================
        print("\n" + "="*80)
        print(" PHASE 6: INITIALIZING STREAMING MARKET FEED WEBSOCKET CHANNELS")
        print("="*80)
        
        websocket_assets = []
        reliance_token = broker._instruments.get_token(symbol="RELIANCE", exchange="NSE", instrument="EQUITY")
        if reliance_token:
            websocket_assets.append(reliance_token)
            
        def diagnostic_tick_callback(tick_packet):
            if tick_packet.get('type') == 'Ticker Data':
                print(f"[{time.strftime('%H:%M:%S')}] TICK DATA RECEIVED -> Token: {tick_packet.get('security_id')} | LTP: {tick_packet.get('LTP')}")

        if websocket_assets:
            logger.info("Launching market feed streaming channel pipeline wrapper. Running for 5 seconds...")
            print("-" * 80)
            broker.start_market_websocket(instruments_list=websocket_assets, on_tick_callback=diagnostic_tick_callback)
            time.sleep(5)
        else:
            logger.warning("Phase 6 Notice: Skipping data stream test due to empty instrument allocations.")

        print("\n" + "="*80)
        print(" DIAGNOSTIC COMPLETE: ALL INFRASTRUCTURE SYSTEMS OPERATING WITHIN PROFILES")
        print("="*80 + "\n")

    except KeyboardInterrupt:
        print("\n" + "="*80)
        logger.info("Diagnostic sequence broken cleanly by manual developer interrupt signal.")
        print("="*80 + "\n")
    except Exception as diagnostic_fault:
        logger.critical(f"System diagnostic crash encountered: {diagnostic_fault}")
    finally:
        logger.info("Executing master security clean down arrays...")
        broker.logout()

if __name__ == "__main__":
    run_rigorous_infrastructure_diagnostic()