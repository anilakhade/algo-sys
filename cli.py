import typer
import os
from dotenv import load_dotenv, set_key
from brokers.dhan_broker import DhanBroker

app = typer.Typer()

@app.command()
def terminal(action: str = "activate"):
    if action == "activate":
        print("System activated")
        print("Venv is ready")
        print("Type: algo login dhan   (or any broker)")
    else:
        print("Unknown action")

@app.command()
def login(broker: str):
    broker = broker.lower()
    print(f"Starting login for {broker.upper()}")

    if broker == "dhan":
        client_id = typer.prompt("Enter DHAN_CLIENT_ID")
        pin = typer.prompt("Enter DHAN_PIN", hide_input=True)
        totp_secret = typer.prompt("Enter DHAN_TOTP_SECRET")

        set_key(".env", "DHAN_CLIENT_ID", client_id)
        set_key(".env", "DHAN_PIN", pin)
        set_key(".env", "DHAN_TOTP_SECRET", totp_secret)

        load_dotenv()

        try:
            b = DhanBroker(client_id, pin, totp_secret)
            token = b.login()
            margin = b.get_margin()
            print("Login successful")
            print("Token received:", token[:30] + "...")
            print("Margin available:", margin)
            print("Dhan is ready to use")
        except Exception as e:
            print("Login failed:", e)

    else:
        print(f"Broker {broker} not supported yet (add later)")

if __name__ == "__main__":
    app()