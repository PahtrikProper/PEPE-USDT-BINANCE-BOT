import ccxt
import pandas as pd
import numpy as np
from ta.volatility import AverageTrueRange
import sys
import time
from datetime import datetime
import threading
import tkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox
import os  # For environment variable access

# ---------------------------- Configuration ---------------------------- #

LOOKBACK = 2                                  # Lookback Period for Trend
SMA18_LENGTH = 3                              # SMA 18 Period
SMA100_LENGTH = 80                            # SMA 100 Period
ATR_MULTIPLIER = 1.5                          # ATR Multiplier for Stop
TRAIL_OFFSET = 0.40                           # Trailing Stop Offset (%)
ATR_PERIOD = 22                               # ATR Period
MIN_BAR_GAP = 24                              # Minimum Bar Gap Between Signals (in candles)
VOLATILITY_SMA_PERIOD = 14                    # SMA period for ATR
VOLUME_SMA_PERIOD = 14                        # SMA period for Volume

SYMBOL = 'PEPE/USDT'
TIMEFRAME = '2h'  # 2-hour intervals
LIMIT = 150        # Number of data points to fetch initially

# ---------------------------- Binance API Setup ---------------------------- #

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_SECRET_KEY')

if not API_KEY or not API_SECRET:
    print("Error: Please set the environment variables 'BINANCE_API_KEY' and 'BINANCE_API_SECRET'.")
    sys.exit(1)

def initialize_binance():
    """
    Initializes the Binance exchange with the provided API key and secret.
    """
    try:
        binance = ccxt.binance({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'enableRateLimit': True,
        })
        binance.load_markets()
        log("Binance Exchange Initialized")
        return binance
    except Exception as e:
        log(f"Error initializing Binance: {e}")
        sys.exit(1)

# ---------------------------- Symbol Verification ---------------------------- #

def verify_symbol(exchange, symbol):
    """
    Verifies if the specified symbol exists on the exchange.
    """
    if symbol in exchange.markets:
        log(f"Symbol {symbol} is available on Binance.")
    else:
        log(f"Symbol {symbol} is NOT available on Binance.")
        log("Available symbols include:")
        available_symbols = list(exchange.markets.keys())[:100]
        formatted_symbols = ', '.join(available_symbols)
        log(formatted_symbols)
        sys.exit(1)

# ---------------------------- Data Retrieval ---------------------------- #

def fetch_data(exchange, symbol, timeframe, limit):
    """
    Fetches historical OHLCV data from Binance.
    """
    log(f"\nFetching {limit} bars of {symbol} data with {timeframe} timeframe...")
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not ohlcv:
            log(f"No OHLCV data returned for {symbol} with timeframe {timeframe}.")
            return pd.DataFrame()
        log(f"Number of bars fetched: {len(ohlcv)}")
    except ccxt.NetworkError as e:
        log(f"Network error while fetching data: {e}")
        return pd.DataFrame()
    except ccxt.ExchangeError as e:
        log(f"Exchange error while fetching data: {e}")
        return pd.DataFrame()
    except Exception as e:
        log(f"An unexpected error occurred while fetching data: {e}")
        return pd.DataFrame()
    
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# ---------------------------- Indicator Calculations ---------------------------- #

def calculate_indicators(df):
    """
    Calculates all necessary indicators for the trading strategy.
    """
    df['ha_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    df['ha_open'] = np.nan
    
    for i in range(len(df)):
        if i == 0:
            entry = (df.iloc[i]['open'] + df.iloc[i]['close']) / 2
            df.at[df.index[i], 'ha_open'] = entry
        else:
            previous_ha_open = df.iloc[i-1]['ha_open']
            previous_ha_close = df.iloc[i-1]['ha_close']
            entry = (previous_ha_open + previous_ha_close) / 2
            df.at[df.index[i], 'ha_open'] = entry
    
    df['ha_high'] = df[['high', 'ha_open', 'ha_close']].max(axis=1)
    df['ha_low'] = df[['low', 'ha_open', 'ha_close']].min(axis=1)
    
    df['trend_ma'] = df['ha_close'].rolling(window=LOOKBACK).mean()
    df['sma100'] = df['close'].rolling(window=SMA100_LENGTH).mean()
    df['sma18'] = df['close'].rolling(window=SMA18_LENGTH).mean()
    
    atr_indicator = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=ATR_PERIOD)
    df['atr'] = atr_indicator.average_true_range()
    
    df['atr_sma'] = df['atr'].rolling(window=VOLATILITY_SMA_PERIOD).mean()
    df['volatility_filter'] = df['atr'] > df['atr_sma']
    
    df['volume_sma'] = df['volume'].rolling(window=VOLUME_SMA_PERIOD).mean()
    df['volume_filter'] = df['volume'] > df['volume_sma']
    
    df['is_doji'] = abs(df['open'] - df['close']) < (df['high'] - df['low']) * 0.1
    df['avoid_doji'] = ~df['is_doji']
    
    def momentum_confirmation_func(df, lookback):
        confirmation = [False]*len(df)
        for i in range(lookback, len(df)):
            condition = True
            for j in range(1, lookback+1):
                if not df.iloc[i - j]['ha_close'] < df.iloc[i - j + 1]['ha_close']:
                    condition = False
                    break
            confirmation[i] = condition
        return confirmation
    
    df['momentum_confirmation'] = momentum_confirmation_func(df, LOOKBACK)
    df.dropna(inplace=True)
    
    return df

# ---------------------------- Trading Actions: Buy and Sell ---------------------------- #

def get_usdt_balance(exchange):
    try:
        balance = exchange.fetch_balance()
        usdt_balance = balance['total']['USDT']
        log(f"USDT Balance: {usdt_balance:.2f}")
        return usdt_balance
    except Exception as e:
        log(f"Error fetching USDT balance: {e}")
        return 0

def get_symbol_balance(exchange, symbol):
    try:
        balance = exchange.fetch_balance()
        symbol_balance = balance['total'][symbol]
        log(f"{symbol} Balance: {symbol_balance:.2f}")
        return symbol_balance
    except Exception as e:
        log(f"Error fetching {symbol} balance: {e}")
        return 0

def get_market_price(exchange, symbol):
    try:
        ticker = exchange.fetch_ticker(symbol)
        last_price = ticker['last']
        log(f"Current {symbol} price: {last_price:.8f} USDT")
        return last_price
    except Exception as e:
        log(f"Error fetching market price: {e}")
        return None

def place_market_buy_order(exchange, symbol, amount):
    """
    Places a market buy order, but first checks for minimum balance requirements.
    """
    try:
        symbol_info = exchange.markets[symbol]
        min_order_value = symbol_info['limits']['cost']['min']

        # Check if amount to be bought is greater than the minimum order value
        price = get_market_price(exchange, symbol)
        order_value = amount * price
        if order_value < min_order_value:
            log(f"Buy skipped: Order value ({order_value:.2f} USDT) is below the minimum allowed ({min_order_value:.2f} USDT).")
            return

        order = exchange.create_market_buy_order(symbol, amount)
        log(f"Market buy order placed for {amount} {symbol.split('/')[0]}! Order details: {order}")
    except Exception as e:
        log(f"Error placing buy order: {e}")

def place_market_sell_order(exchange, symbol, amount):
    """
    Places a market sell order, but first checks for minimum balance requirements.
    """
    try:
        symbol_info = exchange.markets[symbol]
        min_amount = symbol_info['limits']['amount']['min']

        # Check if amount to be sold is greater than the minimum order size
        if amount < min_amount:
            log(f"Sell skipped: Amount ({amount:.2f}) is below the minimum allowed ({min_amount:.2f}).")
            return

        order = exchange.create_market_sell_order(symbol, amount)
        log(f"Market sell order placed for {amount} {symbol.split('/')[0]}! Order details: {order}")
    except Exception as e:
        log(f"Error placing sell order: {e}")

# ---------------------------- Trade Execution ---------------------------- #

def execute_trades(exchange, df, trade_state):
    """
    Places real buy/sell orders based on signals.
    """
    latest_candle = df.iloc[-1]  # Get only the latest candle
    
    current_bar = df.index.get_loc(df.index[-1])

    # Buy Signal
    buy_signal = (
        not trade_state['in_trade'] and
        trade_state['last_signal'] != 1 and
        float(latest_candle['ha_close']) > float(latest_candle['trend_ma']) and
        float(latest_candle['sma18']) > float(latest_candle['sma100']) and
        float(latest_candle['close']) > float(latest_candle['sma100']) and
        latest_candle['momentum_confirmation'] and
        latest_candle['volatility_filter'] and
        latest_candle['volume_filter'] and
        latest_candle['avoid_doji']
    )
    if buy_signal:
        log(f"\n{df.index[-1]} - BUY SIGNAL: Placing real buy order.")
        
        usdt_balance = get_usdt_balance(exchange)
        if usdt_balance <= 0:
            log("Insufficient USDT balance.")
            return
        
        price = get_market_price(exchange, 'PEPE/USDT')
        if price is None:
            return
        
        amount_to_buy = usdt_balance / price
        place_market_buy_order(exchange, 'PEPE/USDT', amount_to_buy)
        
        # Update trade state with entry price and initial trailing stop
        trade_state['entry_price'] = float(latest_candle['close'])
        trade_state['trailing_stop'] = trade_state['entry_price'] - (float(latest_candle['atr']) * ATR_MULTIPLIER)  # Set trailing stop
        trade_state['in_trade'] = True
        trade_state['last_signal'] = 1
        trade_state['last_entry_bar'] = current_bar
        trade_state['last_processed'] = df.index[-1]
        log(f"Set initial trailing stop at: {trade_state['trailing_stop']:.6f} USDT")
        return

    # Update trailing stop (if in a trade)
    if trade_state['in_trade']:
        new_trailing_stop = float(latest_candle['close']) * (1 - TRAIL_OFFSET / 100)  # Trailing stop based on current price
        if new_trailing_stop > trade_state['trailing_stop']:
            trade_state['trailing_stop'] = new_trailing_stop
            log(f"{df.index[-1]} - Trailing Stop Updated: {trade_state['trailing_stop']:.6f} USDT")

    # Sell Signal
    sell_signal = (
        trade_state['in_trade'] and
        trade_state['last_signal'] != -1 and
        (float(latest_candle['close']) <= trade_state['trailing_stop'])
    )
    if sell_signal:
        log(f"\n{df.index[-1]} - SELL SIGNAL: Placing real sell order.")
        
        pepe_balance = get_symbol_balance(exchange, 'PEPE')
        if pepe_balance <= 0:
            log("Insufficient PEPE balance.")
            return
        
        place_market_sell_order(exchange, 'PEPE/USDT', pepe_balance)
        
        # Reset trade state after selling
        trade_state['in_trade'] = False
        trade_state['entry_price'] = None
        trade_state['trailing_stop'] = None  # Reset the trailing stop after exiting the trade
        trade_state['last_signal'] = -1
        trade_state['last_entry_bar'] = current_bar
        trade_state['last_processed'] = df.index[-1]
        return

# ---------------------------- Logging Mechanism ---------------------------- #

log_widget = None

def log(message):
    """
    Logs messages to the GUI log display.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[{timestamp}] {message}\n"
    if log_widget:
        log_widget.configure(state='normal')
        log_widget.insert(tk.END, full_message)
        log_widget.configure(state='disabled')
        log_widget.see(tk.END)
    else:
        print(full_message, end='')

# ---------------------------- Main Execution ---------------------------- #

def trading_loop(stop_event):
    """
    The main trading loop to be run in a separate thread.
    """
    exchange = initialize_binance()
    verify_symbol(exchange, SYMBOL)
    
    trade_state = {
        'in_trade': False,
        'entry_price': None,
        'trailing_stop': None,  # Initialize trailing stop to None
        'last_signal': 0,
        'last_entry_bar': -MIN_BAR_GAP,
        'last_processed': pd.Timestamp.min
    }
    
    while not stop_event.is_set():
        df = fetch_data(exchange, SYMBOL, TIMEFRAME, LIMIT)
        if df.empty:
            log("No data fetched. Retrying in 5 minutes...")
            for _ in range(300):
                if stop_event.is_set():
                    break
                time.sleep(1)
            continue
        
        df_calculated = calculate_indicators(df)
        execute_trades(exchange, df_calculated, trade_state)

        unit = ''.join(filter(str.isalpha, TIMEFRAME))
        number = ''.join(filter(str.isdigit, TIMEFRAME))
        number = int(number) if number else 1
        sleep_duration = number * {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}.get(unit, 3600)
        
        log(f"\nWaiting for the next {TIMEFRAME} candle...")
        for _ in range(sleep_duration):
            if stop_event.is_set():
                break
            time.sleep(1)

    log("Trading loop stopped.")

def start_trading():
    """
    Starts the trading in a separate thread.
    """
    global trading_thread
    if trading_thread and trading_thread.is_alive():
        messagebox.showwarning("Warning", "Trading is already running.")
        return
    stop_event.clear()
    trading_thread = threading.Thread(target=trading_loop, args=(stop_event,), daemon=True)
    trading_thread.start()
    log("Trading started.")

def stop_trading():
    """
    Stops the trading gracefully.
    """
    global trading_thread
    if trading_thread and trading_thread.is_alive():
        stop_event.set()
        trading_thread.join()
        log("Trading stopped.")
    else:
        messagebox.showinfo("Info", "Trading is not running.")

def on_closing():
    """
    Handles the window closing event.
    """
    if trading_thread and trading_thread.is_alive():
        if messagebox.askokcancel("Quit", "Trading is running. Do you want to quit?"):
            stop_event.set()
            trading_thread.join()
            root.destroy()
    else:
        root.destroy()

stop_event = threading.Event()
trading_thread = None

# ---------------------------- GUI Setup ---------------------------- #

root = tk.Tk()
root.title("Trading Bot")
root.geometry("900x900")

button_frame = tk.Frame(root)
button_frame.pack(pady=10)

start_button = tk.Button(button_frame, text="Start Trading", command=start_trading, width=15, bg='green', fg='white')
start_button.pack(side='left', padx=10)

stop_button = tk.Button(button_frame, text="Stop Trading", command=stop_trading, width=15, bg='red', fg='white')
stop_button.pack(side='left', padx=10)

log_widget = scrolledtext.ScrolledText(root, state='disabled', wrap='word', width=120, height=40)
log_widget.pack(padx=10, pady=10, fill='both', expand=True)

import builtins
builtins.print = lambda message, end='\n': log(message)

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
