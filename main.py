import os
import sys
import logging
import time
from dotenv import load_dotenv

from brokers.dhan_broker import DhanBroker
from src.database import PaperDatabase
from src.paper_engine import PaperEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger("Paper_Desk_Orchestrator")

load_dotenv()

def initialize_and_run_paper_trading_desk():
    logger.info("Initializing multi-tenant virtual trading desk environment...")

    # 1. Instantiate Core Subsystems
    db = PaperDatabase()
    if not db.client:
        logger.critical("Initialization Aborted: Supabase client connection failure.")
        return

    paper_broker = PaperEngine(db_client=db)
    
    broker = DhanBroker(
        client_id=os.getenv("DHAN_CLIENT_ID"),
        pin=os.getenv("DHAN_PIN"),
        totp_secret=os.getenv("DHAN_TOTP_SECRET")
    )

    try:
        # 2. Authenticate Live Broker & Sync Network IP Gateways
        session_token = broker.login()
        if not session_token:
            logger.error("Failed to establish master broker link session.")
            return

        # 3. Provision Multi-Account Sandboxes
        print("\n" + "="*80)
        print(" CONFIGURING PAPER TRADING ACCOUNTS & STRATEGY MATRICES INSIDE SUPABASE")
        print("="*80)
        
        # Profile Account A: Statistical Arbitrage Desk
        acc_a_id = "ACC_ARB_001"
        logger.info(f"Provisioning {acc_a_id} (Arbitrage Desk) with INR 2,500,000...")
        db.create_paper_account(account_id=acc_a_id, account_name="Stat-Arb Shared Pool", initial_cash=2500000.00)
        db.create_strategy_instance(strategy_id="STRAT_CASH_FUT", account_id=acc_a_id, name="Cash-Fut Convergence", strat_type="STAT_ARB", capital=1500000.00)
        db.create_strategy_instance(strategy_id="STRAT_PAIR_TRADE", account_id=acc_a_id, name="High-Freq Mean Reversion", strat_type="STAT_ARB", capital=1000000.00)

        # Profile Account B: Pure Options Derivatives Sandbox
        acc_b_id = "ACC_OPT_002"
        logger.info(f"Provisioning {acc_b_id} (Options Sandbox) with INR 1,000,000...")
        db.create_paper_account(account_id=acc_b_id, account_name="Options Theta Sandbox", initial_cash=1000000.00)
        db.create_strategy_instance(strategy_id="STRAT_IRON_CONDOR", account_id=acc_b_id, name="Weekly Nifty Condor", strat_type="OPTIONS_SPREAD", capital=1000000.00)

        # 4. Verify Post-Provisioning Cloud Account States
        state_check = db.get_account_state(acc_a_id)
        print(f"\n -> Confirmed Cloud State for {acc_a_id}:")
        print(f"    Name: {state_check.get('account_name')} | Cash Balance: INR {state_check.get('current_cash')} | Status: ACTIVE")

        # 5. Run Pre-Trade Simulation Order Check
        print("\n" + "="*80)
        print(" TESTING SIMULATED RISK RULES & ACCOUNTS TRANSACTION ENTRY LOGS")
        print("="*80)
        
        tata_token = broker._instruments.get_token(symbol="TATASTEEL", exchange="NSE", instrument="EQUITY")
        if tata_token:
            # Construct a dummy order packet for our virtual engine matchmaker
            sim_order_packet = {
                "token": tata_token["token"],
                "symbol": "TATASTEEL",
                "exchange": tata_token["exchange"],
                "segment": tata_token["segment"],
                "direction": "BUY",
                "quantity": 100,
                "order_type": "LIMIT",
                "product_type": "MIS",
                "price": 165.50
            }
            
            logger.info("Injecting virtual 100 share limit order packet into Account ACC_ARB_001...")
            sim_result = paper_broker.place_virtual_order(account_id=acc_a_id, strategy_id="STRAT_CASH_FUT", order_packet=sim_order_packet)
            
            print(f" -> Simulator Matchmaker Response: {sim_result.get('status').upper()}")
            print(f"    Execution Price (With Friction Added): INR {sim_result.get('execution_price', 0.0):.2f}")
            print(f"    Margin Allocated and Locked to Desk : INR {sim_result.get('margin_locked', 0.0):.2f}")
            print(f"    Matching Engine Remarks             : {sim_result.get('remarks')}")
            
            # Re-read account tracking metrics to show dynamic margin updates
            updated_state = db.get_account_state(acc_a_id)
            print(f" -> Post-Trade Available Risk Margin: INR {updated_state.get('available_margin')}")
            print(f" -> Post-Trade Total Capital Locked : INR {updated_state.get('utilized_margin')}")

        # 6. Bind the Live Streaming Feed directly to the Virtual Accountant
        print("\n" + "="*80)
        print(" LINKING LIVE WEB_SOCKET STREAM INTO VIRTUAL LEDGER ENGINE")
        print("="*80)
        
        reliance_token = broker._instruments.get_token(symbol="RELIANCE", exchange="NSE", instrument="EQUITY")
        if reliance_token:
            logger.info("Registering virtual position ledger tracker to watch for RELIANCE ticks...")
            
            # When the real-world websocket receives a price change, it passes it straight 
            # to paper_broker.handle_market_tick. The engine recalculates the live floating 
            # PnL for all active accounts inside your Supabase tables in micro-seconds.
            broker.start_market_websocket(
                instruments_list=[reliance_token], 
                on_tick_callback=paper_broker.handle_market_tick
            )
            
            logger.info("Trading desk pipeline active. Processing background telemetry stream for 5 seconds...")
            time.sleep(5)

        print("\n" + "="*80)
        print(" TELEMETRY SHUTDOWN: GRACEFULLY CLOSING CORE DESK EXECUTION RUNTIMES")
        print("="*80 + "\n")

    except KeyboardInterrupt:
        print("\n")
        logger.info("System execution cut cleanly by developer keyboard signal.")
    except Exception as run_err:
        logger.critical(f"Platform architecture crashed inside master engine: {run_err}")
    finally:
        logger.info("Clearing memory handlers and closing sessions safely...")
        broker.logout()

if __name__ == "__main__":
    initialize_and_run_paper_trading_desk()