import pyupbit
import datetime
import time
import logging


logging.basicConfig(filename='trading.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

access = "your_access_key"  
secret = "your_secret_key"  
upbit = pyupbit.Upbit(access, secret)

def cancel_unfilled_orders():
    
    try:
        orders = upbit.get_order(state="wait")
        for order in orders:
            upbit.cancel_order(order['uuid'])
    except TimeoutError as e:
        logging.error(f"Timeout occurred: {e}")
    except ValueError as e:
        logging.error(f"Value error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

def get_ma(ticker, days):
    
    try:
        df = pyupbit.get_ohlcv(ticker, interval="day", count=days)
        ma = df['close'].rolling(window=days).mean().iloc[-1]
        return ma
    except TimeoutError as e:
        logging.error(f"Timeout occurred: {e}")
    except ValueError as e:
        logging.error(f"Value error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return None

def check_market_timing():
    
    btc_price = pyupbit.get_current_price("KRW-BTC")
    if btc_price is None:
        return False
    ma2 = get_ma("KRW-BTC", 2)
    ma4 = get_ma("KRW-BTC", 4)
    ma8 = get_ma("KRW-BTC", 8)
    ma120 = get_ma("KRW-BTC", 120)
    if ma2 is None or ma4 is None or ma8 is None or ma120 is None:
        return False
    if (btc_price > ma2 or btc_price > ma4 or btc_price > ma8) and btc_price > ma120:
        return True
    else:
        return False

def get_top_gainers():
    
    try:
        tickers = pyupbit.get_tickers(fiat="KRW")
        gainers = []
        for ticker in tickers:
            ohlcv = pyupbit.get_ohlcv(ticker, interval="day", count=2)
            if len(ohlcv) < 2:
                continue
            close = ohlcv['close']
            change = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]
            gainers.append((ticker, change))
        gainers.sort(key=lambda x: x[1], reverse=True)
        return [gainer[0] for gainer in gainers[:6]]
    except TimeoutError as e:
        logging.error(f"Timeout occurred: {e}")
    except ValueError as e:
        logging.error(f"Value error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return []


def trade():
    
    try:
        now = datetime.datetime.now()
        if now.hour == 8 and now.minute == 59:
            cancel_unfilled_orders()
        elif now.hour == 9 and now.minute == 0:  
            owned_coins = upbit.get_balances()
            for coin in owned_coins:
                ticker = f"KRW-{coin['currency']}"
                ohlcv = pyupbit.get_ohlcv(ticker, interval="day", count=2)               
                purchase_price = coin['avg_buy_price']  
                current_price = ohlcv['close'][-1]  
                profit_rate = (current_price - float(purchase_price)) / float(purchase_price) * 100  # 수익률 계산            
                if profit_rate < 10:  
                    sell_price = ohlcv['close'][-2]  
                    upbit.sell_limit_order(ticker, sell_price, coin['balance'])
                elif profit_rate >= 10:
                    pivot = (ohlcv['high'][-1] + ohlcv['low'][-1] + ohlcv['close'][-1]) / 3
                    resistance = pivot * 2 - ohlcv['low'][-1]
                    if coin['balance'] * resistance > 5000:  
                        upbit.sell_limit_order(ticker, resistance, coin['balance'])        
        elif now.hour == 9 and now.minute == 1:
            if check_market_timing():
                gainers = get_top_gainers()
                if not gainers:
                    return
                balance = upbit.get_balance("KRW")
                for ticker in gainers:
                    ohlcv = pyupbit.get_ohlcv(ticker, interval="day", count=1)
                    pivot = (ohlcv['high'][-1] + ohlcv['low'][-1] + ohlcv['close'][-1]) / 3
                    support = pivot * 2 - ohlcv['high'][-1]
                    amount = balance / 1000 / support
                    upbit.buy_limit_order(ticker, support, amount)
    except TimeoutError as e:
        logging.error(f"Timeout occurred: {e}")
    except ValueError as e:
        logging.error(f"Value error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

def is_time_to_execute():
    now = datetime.datetime.now()
    

    start_time = now.replace(hour=8, minute=55, second=0, microsecond=0)
    end_time = now.replace(hour=9, minute=5, second=0, microsecond=0)
    

    if start_time <= now <= end_time:
        return True
    else:
        return False

if __name__ == "__main__":
    while True:
        if is_time_to_execute():
            print("Executing trade logic")

        else:
            print("Current time is not within working period")
        

        time.sleep(60)
