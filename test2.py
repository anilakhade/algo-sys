import os
import sys
from dotenv import load_dotenv
from brokers.dhan_broker import DhanBroker

load_dotenv()

client_id = os.getenv("DHAN_CLIENT_ID")
pin = os.getenv("DHAN_PIN")
totp_secret = os.getenv("DHAN_TOTP_SECRET")

if not all([client_id, pin, totp_secret]):
    print("Error: Credentials missing from .env file")
    sys.exit(1)

broker = DhanBroker(client_id=client_id, pin=pin, totp_secret=totp_secret)
session = broker.login()

if not session:
    print("Error: Login session authentication failed")
    sys.exit(1)

leg1 = broker._instruments.get_token(
    symbol="CRUDEOIL",
    exchange="MCX",
    instrument="OPTFUT",
    expiry="16 JUN",
    strike=7600.0,
    option_type="CE"
)

leg2 = broker._instruments.get_token(
    symbol="CRUDEOIL",
    exchange="MCX",
    instrument="OPTFUT",
    expiry="16 JUN",
    strike=7600.0,
    option_type="PE"
)

if not leg1 or not leg2:
    print("Error: Options tokens not resolved from master index mapping")
    sys.exit(1)

qty1 = 10 * int(leg1.get("lot_size", 100))
qty2 = 10 * int(leg2.get("lot_size", 100))

packets = [
    {
        "exchange": "MCX",
        "segment": "OPTFUT",
        "direction": "SELL",
        "quantity": qty1,
        "token": leg1["token"],
        "price": 110.0,
        "product_type": "INTRADAY"
    },
    {
        "exchange": "MCX",
        "segment": "OPTFUT",
        "direction": "SELL",
        "quantity": qty2,
        "token": leg2["token"],
        "price": 127.0,
        "product_type": "INTRADAY"
    }
]

margin_results = broker.calculate_strategy_margin(packets)
print("Margin Matrix Response Data:", margin_results)

sdk_client = broker._login.get_client()

try:
    if hasattr(sdk_client, "get_ltp"):
        ltp_query = [("MCX_COMM", leg1["token"]), ("MCX_COMM", leg2["token"])]
        ltp_response = sdk_client.get_ltp(ltp_query)
        ltp1 = float(ltp_response["data"]["MCX_COMM"][leg1["token"]]["last_price"])
        ltp2 = float(ltp_response["data"]["MCX_COMM"][leg2["token"]]["last_price"])
    else:
        res1 = sdk_client.get_quote(security_id=leg1["token"], exchange_segment="MCX_COMM")
        res2 = sdk_client.get_quote(security_id=leg2["token"], exchange_segment="MCX_COMM")
        
        data1 = res1.get("data", res1)
        data2 = res2.get("data", res2)
        
        ltp1 = float(data1.get("lastPrice") or data1.get("last_price") or 0.0)
        ltp2 = float(data2.get("lastPrice") or data2.get("last_price") or 0.0)

    mtm1 = (110.0 - ltp1) * qty1
    mtm2 = (127.0 - ltp2) * qty2
    total_mtm = mtm1 + mtm2
    
    print(f"CE Target ID: {leg1['token']} | Execution: 110.0 | Spot Price: {ltp1} | Net Yield MTM: {mtm1}")
    print(f"PE Target ID: {leg2['token']} | Execution: 127.0 | Spot Price: {ltp2} | Net Yield MTM: {mtm2}")
    print(f"Combined Position Portfolio MTM: {total_mtm}")
except Exception as error:
    print("Metrics compilation fault parsing dynamic value chains:", error)