
# PEPE/USDT Binance Trading Bot

This bot implements a technical analysis strategy to trade the PEPE/USDT pair on Binance. It uses several technical indicators such as Heikin Ashi candles, moving averages, volatility filters (ATR), and volume filters to determine buy and sell signals.

## Strategy Overview

The bot operates on the following principles:
- **Heikin Ashi Candles**: A type of candlestick chart used to identify trends and reversals more clearly.
- **SMA (Simple Moving Average)**: Two SMAs are used:
  - `SMA18`: A short-term SMA based on the closing price of the last 18 candles.
  - `SMA100`: A long-term SMA based on the closing price of the last 100 candles.
- **ATR (Average True Range)**: Used for setting the trailing stop to exit trades when the market reverses.
- **Volume and Volatility Filters**: The bot uses volatility and volume filters to avoid trading during low-volume and low-volatility periods.
- **Trailing Stop**: The bot sets a trailing stop when a buy signal is triggered. If the price drops to the trailing stop, the bot sells the position.
- **Buy/Sell Logic**:
  - **Buy Signal**: When certain conditions related to moving averages, momentum, and volume are met, the bot enters a buy position.
  - **Sell Signal**: The bot exits the trade (sells) when the price hits the trailing stop or the price action reverses.

## Required Modules

The bot uses the following Python modules:

1. **ccxt**: For interacting with the Binance API and placing real orders.
2. **pandas**: For handling the historical OHLCV data and indicators.
3. **numpy**: For numerical operations.
4. **ta-lib**: Specifically `ta.volatility.AverageTrueRange` to calculate the ATR.
5. **tkinter**: For creating a graphical interface (optional, but included for visualizing logs).
6. **time**, **sys**, **os**, **datetime**: Standard Python libraries for handling timing, system operations, and date-time functions.

To install the required modules, use the following commands:

```bash
pip install ccxt pandas numpy ta-lib
```

For **Tkinter**, it should be available in most Python distributions. However, if you face issues, you can install it via the following:

- On **Linux**:
  ```bash
  sudo apt-get install python3-tk
  ```

- On **Windows/Mac**, Tkinter is included with Python.

## How the Bot Works

1. **Initialization**:
   - The bot first connects to Binance using the `ccxt` library.
   - It verifies if the trading symbol (`PEPE/USDT`) is available on Binance.
   
2. **Fetching Data**:
   - The bot fetches historical OHLCV data (Open, High, Low, Close, Volume) from Binance.
   - It then calculates the required technical indicators: Heikin Ashi candles, SMAs, ATR, and volume filters.
   
3. **Buy Signal**:
   - The bot looks for a valid buy signal when:
     - Heikin Ashi close is above the trend moving average.
     - Short-term `SMA18` is above the long-term `SMA100`.
     - Momentum confirmation is positive (uptrend), and volatility/volume filters are satisfied.
   - If these conditions are met, the bot checks if there is sufficient USDT balance to place an order and if so, places a market buy order.

4. **Sell Signal**:
   - The bot sets a **trailing stop** based on the ATR.
   - If the price falls below the trailing stop or meets other exit criteria, the bot checks the available PEPE balance and places a market sell order.

5. **Logs and GUI**:
   - The bot outputs logs detailing every action (buy, sell, error, etc.) either in a Tkinter GUI or in the console if Tkinter is unavailable.

## Running the Bot in Visual Studio Code

### Prerequisites

- **Python**: Ensure Python 3.x is installed on your machine.
- **API Keys**: You need to get API keys from your Binance account.
  - **API_KEY**: Your Binance API key.
  - **API_SECRET**: Your Binance secret key.
  
  These should be set as environment variables on your system:
  - On **Windows**:
    ```bash
    setx BINANCE_API_KEY "your_api_key"
    setx BINANCE_SECRET_KEY "your_api_secret"
    ```
  - On **Linux/macOS**:
    ```bash
    export BINANCE_API_KEY="your_api_key"
    export BINANCE_SECRET_KEY="your_api_secret"
    ```

### Steps to Run the Bot

1. **Install Visual Studio Code (VS Code)**:
   - Download and install VS Code from [here](https://code.visualstudio.com/).
   
2. **Set Up the Python Environment**:
   - Open VS Code and install the **Python** extension if you haven't already.
   - Open a terminal in VS Code and create a virtual environment (optional but recommended):
     ```bash
     python -m venv env
     ```
   - Activate the virtual environment:
     - On **Windows**:
       ```bash
       .\env\Scriptsctivate
       ```
     - On **macOS/Linux**:
       ```bash
       source env/bin/activate
       ```

3. **Install the Required Modules**:
   In the VS Code terminal, install the required Python libraries:

   ```bash
   pip install ccxt pandas numpy ta-lib
   ```

4. **Copy the Bot Script**:
   - Copy the provided bot script (`PEPE USDT BINANCE TRADER.py`) into a new file in your VS Code workspace.
   - Ensure the API keys are properly set as environment variables.

5. **Run the Bot**:
   - In VS Code, open the Python file and click on the "Run" button at the top or press `F5` to run the script.
   - The bot will start fetching data and trading based on the conditions defined.

6. **Stop the Bot**:
   - To stop the bot, you can press `Ctrl+C` in the terminal or stop it from the GUI (if you are using the Tkinter version).

### Important Notes

- **Live Trading**: This bot will place real trades on Binance when a buy or sell signal is detected. Ensure that your API key has **trading permissions** and that you're aware of the risks involved in automated trading.
- **Paper Trading**: You may want to test this bot using Binance's testnet API to avoid real trades until you are confident. Testnet API setup requires different keys, which you can find in Binance's documentation.

## Example Outputs

When running, the bot will log all actions in the console (or in the Tkinter window if the GUI is enabled). Example log output:

```
[2024-10-01 14:30:12] Fetching 150 bars of PEPE/USDT data with 2h timeframe...
[2024-10-01 14:30:13] Symbol PEPE/USDT is available on Binance.
[2024-10-01 14:32:45] BUY SIGNAL: Placing real buy order.
[2024-10-01 14:32:45] USDT Balance: 528.00
[2024-10-01 14:32:46] Market buy order placed for 55991953.00 PEPE!
[2024-10-01 16:34:12] Trailing Stop Updated: 0.00000890 USDT
[2024-10-01 18:36:20] SELL SIGNAL: Placing real sell order.
[2024-10-01 18:36:21] Market sell order placed for 55991953.00 PEPE!
```

## License

This project is provided under the MIT License.
