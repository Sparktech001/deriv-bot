


import websocket
import json
import pandas as pd
import time

# Deriv API Token (Use your own API key here)
API_TOKEN = "6Agc12pHjzXtDl3"

# Define WebSocket URL
DERIV_WS_URL = "wss://ws.binaryws.com/websockets/v3?app_id=69103"

# Initialize WebSocket
ws = websocket.WebSocket()
ws.connect(DERIV_WS_URL)

# Authenticate with API Token and Fetch Account Balance
def authenticate():
    auth_request = json.dumps({"authorize": API_TOKEN})
    ws.send(auth_request)
    response = json.loads(ws.recv())
    if "authorize" in response:
        account_info = response["authorize"]
        print("✅ Authenticated successfully!")
        print(f"🔹 Account Type: {'Real' if account_info['is_virtual'] == 0 else 'Demo'}")
        print(f"💰 Balance: {account_info['balance']} {account_info['currency']}")
    else:
        print("❌ Authentication failed!", response)
        exit()

authenticate()

# Subscribe to market data
def subscribe_to_ticks():
    sub_request = json.dumps({
        "ticks": "R_100",
        "subscribe": 1
    })
    ws.send(sub_request)

def get_tick_data():
    data = json.loads(ws.recv())
    if "tick" in data:
        return {
            "epoch": pd.to_datetime(data["tick"]["epoch"], unit="s"),
            "price": float(data["tick"]["quote"])
        }
    return None

# Initialize trade parameters
risk_per_trade = 0.01  # 1% of account balance per trade
account_balance = 100  # Starting balance (Adjust as needed)
trade_amount = account_balance * risk_per_trade

def calculate_trade_amount():
    return account_balance * risk_per_trade

# Placeholder for RSI & Breakout Strategy
price_data = []  # Store recent prices
rsi_period = 14

# RSI Calculation
def calculate_rsi(prices, period=14):
    if len(prices) < period:
        return None  # Not enough data
    df = pd.DataFrame(prices, columns=["price"])
    df["delta"] = df["price"].diff()
    df["gain"] = df["delta"].apply(lambda x: x if x > 0 else 0)
    df["loss"] = df["delta"].apply(lambda x: -x if x < 0 else 0)
    avg_gain = df["gain"].rolling(window=period, min_periods=1).mean()
    avg_loss = df["loss"].rolling(window=period, min_periods=1).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# Trading logic
def check_trade_signal(tick_data):
    global account_balance
    price_data.append(tick_data["price"])
    if len(price_data) > rsi_period:
        price_data.pop(0)  # Keep data size fixed

    rsi = calculate_rsi(price_data, rsi_period)
    if rsi is None:
        return

    # Breakout logic (Simple example: Price breaks above recent high for buy, below recent low for sell)
    recent_high = max(price_data[-rsi_period:])
    recent_low = min(price_data[-rsi_period:])

    if tick_data["price"] > recent_high and rsi < 70:
        place_trade("long")
    elif tick_data["price"] < recent_low and rsi > 30:
        place_trade("short")

# Place a trade
def place_trade(direction):
    global account_balance
    trade_amount = calculate_trade_amount()
    trade_request = json.dumps({
        "buy": 1,
        "parameters": {
            "amount": trade_amount,
            "basis": "stake",
            "contract_type": "CALL" if direction == "long" else "PUT",
            "currency": "USD",
            "duration": 5,
            "duration_unit": "m",
            "symbol": "R_100"
        }
    })
    ws.send(trade_request)
    response = json.loads(ws.recv())
    print(f"Trade placed ({direction}):", response)

    if "buy" in response:
        account_balance += trade_amount * 3  # 3:1 RR assumed
    else:
        account_balance -= trade_amount  # Loss

# Run bot
subscribe_to_ticks()
while True:
    tick = get_tick_data()
    if tick:
        check_trade_signal(tick)
    time.sleep(1)