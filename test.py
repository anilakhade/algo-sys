import os
import sys
import logging
import time
from dotenv import load_dotenv

# 1. Setup localized logging profile
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger("Hybrid_Feed_Tester")

try:
    from brokers.dhan.login import DhanAuth
    from brokers.dhan.instruments import DhanInstruments
    from brokers.dhan.websocket import DhanWebSocket
except ImportError as e:
    logger.error(f"System architecture import fault: {e}")
    sys.exit(1)

load_dotenv()

def execute_hybrid_system_test():
    logger.info("Initializing multi-exchange hybrid lookup test...")

    client_id = os.getenv("DHAN_CLIENT_ID")
    pin = os.getenv("DHAN_PIN")
    totp_secret = os.getenv("DHAN_TOTP_SECRET")

    if not all([client_id, pin, totp_secret]):
        logger.error("Configuration Failure: Secure credentials missing from .env context.")
        return

    # Instantiate our modules
    auth = DhanAuth(client_id=client_id, pin=pin, totp_secret=totp_secret)
    instruments = DhanInstruments(auth_provider=auth)
    ws = DhanWebSocket(auth_provider=auth)

    try:
        # Step A: Authentication Handshake
        auth.execute()
        
        # Step B: Boot & compile memory maps
        instruments.download()

        # Step C: Execute our specific asset lookups following the new parsing boundaries
        logger.info("Resolving targeted test assets from compiled memory maps...")
        active_subscriptions = []

        # 1. Test NSE Equity Cash (Uses standard Ticker Symbol)
        infy_cash = instruments.get_token(symbol="INFY", exchange="NSE", instrument="EQUITY")
        if infy_cash: active_subscriptions.append(infy_cash)

        # 2. Test BSE Equity Cash (Uses standard Ticker Symbol cross-verify)
        tcs_bse = instruments.get_token(symbol="TCS", exchange="BSE", instrument="EQUITY")
        if tcs_bse: active_subscriptions.append(tcs_bse)

        # 3. Test Spot Index (Uses standard Ticker Symbol)
        nifty_spot = instruments.get_token(symbol="NIFTY", exchange="NSE", instrument="INDEX")
        if nifty_spot: active_subscriptions.append(nifty_spot)

        # 4. Test Index Future (Requires just the Expiry Month name)
        nifty_fut = instruments.get_token(symbol="NIFTY", exchange="NSE", instrument="FUTIDX", expiry="JUN")
        if nifty_fut: active_subscriptions.append(nifty_fut)

        # 5. Test Index Option (Requires DAY MONTH format, clean numeric strike, and CE/PE)
        # Note: We try a generic strike cluster to safely catch current month contracts
        nifty_opt = instruments.get_token(symbol="NIFTY", exchange="NSE", instrument="OPTIDX", expiry="25 JUN", strike=23000, option_type="CE")
        if nifty_opt: 
            active_subscriptions.append(nifty_opt)
        else:
            # Fallback check for another common expiry day if 25 JUN isn't present in the current master file
            logger.info("Checking alternate option contract expiry match...")
            nifty_opt_alt = instruments.get_token(symbol="NIFTY", exchange="NSE", instrument="OPTIDX", expiry="18 JUN", strike=23500, option_type="PE")
            if nifty_opt_alt: active_subscriptions.append(nifty_opt_alt)

        # 6. Test MCX Commodity Future (Requires Expiry Month name)
        crude_fut = instruments.get_token(symbol="CRUDEOIL", exchange="MCX", instrument="FUTCOM", expiry="JUN")
        if crude_fut: active_subscriptions.append(crude_fut)

        print("\n" + "=" * 70)
        print("                HYBRID MASTER EXTRACTION RESULTS")
        print("=" * 70)
        logger.info(f"Successfully resolved {len(active_subscriptions)} targeted assets for streaming:")
        for asset in active_subscriptions:
            print(f" -> Ticker: {asset['trading_symbol']:<25} | Token: {asset['token']:<8} | Exch: {asset['exchange']:<4} | Seg: {asset['segment']}")
        print("=" * 70 + "\n")

        if not active_subscriptions:
            logger.error("Test Terminated: Zero assets successfully resolved from the database matrix.")
            return

        # Step D: Define structural feed callback handler
        def data_stream_monitor(tick_frame):
            print(f"[{time.strftime('%H:%M:%S')}] TICK INCOMING -> Seg ID: {tick_frame.get('exchange_segment')} | Token: {tick_frame.get('security_id')} | Price: {tick_frame.get('LTP')}")

        # Step E: Ignite WebSocket engine layer stream loop
        logger.info("Injecting resolved tokens into websocket live pipe. Press Ctrl+C to stop.")
        print("-" * 70)
        
        ws.start_market(instruments_list=active_subscriptions, on_tick_callback=data_stream_monitor)

    except KeyboardInterrupt:
        print("\n" + "=" * 70)
        logger.info("Keyboard Interrupt caught. Exiting test safely...")
        print("=" * 70)
    except Exception as run_error:
        logger.critical(f"Standalone pipeline test crashed: {run_error}")
    finally:
        logger.info("Purging authentication context footprint...")
        auth.logout()

if __name__ == "__main__":
    execute_hybrid_system_test()