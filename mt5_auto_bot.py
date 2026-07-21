import MetaTrader5 as mt5
import firebase_admin
from firebase_admin import credentials, firestore
import time
import os
import threading

# =====================================================================
# MT5 Auto-Trading Execution Bot
# =====================================================================
# IMPORTANT: This script MUST run on a Windows machine with MT5 installed.
# It listens to Firebase for AI trading signals and executes them instantly.

# ⬇️ ضع بيانات حسابك في MT5 هنا ⬇️
MT5_LOGIN = 0  # ضع رقم الحساب هنا كأرقام، مثلاً: 12345678 (بدون علامات تنصيص)
MT5_PASSWORD = ""  # ضع الباسورد هنا بين علامتي التنصيص
MT5_SERVER = ""  # ضع اسم سيرفر الشركة هنا، مثلاً: "Exness-MT5Trial6"

def init_mt5():
    if not mt5.initialize():
        print("❌ initialize() failed, error code =", mt5.last_error())
        quit()
        
    if MT5_LOGIN != 0 and MT5_PASSWORD != "":
        authorized = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
        if authorized:
            print(f"✅ Logged in to MT5 Account: {MT5_LOGIN}")
        else:
            print(f"❌ Failed to connect to account #{MT5_LOGIN}, error code: {mt5.last_error()}")
            quit()
    else:
        print("✅ Connected to MT5 successfully! (Using currently active account)")

def init_firebase():
    key_path = "serviceAccountKey.json"
    if not os.path.exists(key_path):
        print("❌ Firebase credentials not found! Please place 'serviceAccountKey.json' in this folder.")
        quit()
    
    cred = credentials.Certificate(key_path)
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)
    
    print("✅ Connected to Firebase successfully!")
    return firestore.client()

def execute_trade(signal_id, data, db):
    # Check if credentials were sent from website
    app_login = data.get("mt5_login")
    app_pass = data.get("mt5_password")
    app_server = data.get("mt5_server")
    
    if app_login and app_pass:
        try:
            l = int(app_login)
            if mt5.login(l, password=app_pass, server=app_server):
                print(f"✅ Web Credentials: Logged in to account {l}")
            else:
                print(f"❌ Web Credentials: Login failed, error {mt5.last_error()}")
        except Exception as e:
            print("❌ Web Credentials format error:", e)

    symbol = data.get("symbol")
    action = data.get("action")
    lot_size = float(data.get("lot_size", 0.01))
    sl = float(data.get("sl", 0))
    tp = float(data.get("tp", 0))
    
    print(f"\\n🚀 EXECUTION TRIGGERED: {action} {symbol} | Lot: {lot_size} | SL: {sl} | TP: {tp}")
    
    # Select symbol in Market Watch
    if not mt5.symbol_select(symbol, True):
        print(f"❌ Failed to select {symbol}")
        db.collection("mt5_signals").document(signal_id).update({"status": "FAILED", "reason": "Symbol not found"})
        return
    
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"❌ {symbol} not found.")
        db.collection("mt5_signals").document(signal_id).update({"status": "FAILED", "reason": "Symbol info None"})
        return
        
    order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
    price = mt5.symbol_info_tick(symbol).ask if action == "BUY" else mt5.symbol_info_tick(symbol).bid
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 100100,
        "comment": "AI AutoTrade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Order failed, retcode={result.retcode}")
        db.collection("mt5_signals").document(signal_id).update({
            "status": "FAILED",
            "reason": f"MT5 Error: {result.retcode}"
        })
    else:
        print(f"✅ Order executed successfully! Ticket: {result.order}")
        db.collection("mt5_signals").document(signal_id).update({
            "status": "EXECUTED",
            "ticket": result.order,
            "exec_price": result.price
        })

def listen_for_signals():
    init_mt5()
    db = init_firebase()
    
    print("\\n🎧 Listening for AI Trading Signals from the Cloud...")
    print("Keep this window open to allow automatic trading.\\n")

    # Create an Event to block the main thread
    callback_done = threading.Event()

    def on_snapshot(col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == 'ADDED':
                data = change.document.to_dict()
                if data.get("status") == "PENDING":
                    execute_trade(change.document.id, data, db)

    # Watch the collection for new signals
    col_query = db.collection("mt5_signals").where("status", "==", "PENDING")
    doc_watch = col_query.on_snapshot(on_snapshot)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\\n🛑 Stopping MT5 Executor Bot...")
        mt5.shutdown()

if __name__ == "__main__":
    listen_for_signals()
