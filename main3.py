import pyupbit
import datetime
import time
import logging

# 로깅 설정 개선
logging.basicConfig(filename='trading.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

access = "your_access_key"  # 여기에 업비트에서 발급받은 Access Key를 입력하세요.
secret = "your_secret_key"  # 여기에 업비트에서 발급받은 Secret Key를 입력하세요.
upbit = pyupbit.Upbit(access, secret)

def cancel_unfilled_orders():
    """미체결 매수 주문을 취소합니다."""
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
    """이동 평균을 계산합니다."""
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
    """마켓 타이밍을 확인합니다."""
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
    """전봉 상승률이 가장 높았던 6종목을 찾습니다."""
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
    """매수 및 매도 로직을 실행합니다."""
    try:
        now = datetime.datetime.now()
        if now.hour == 8 and now.minute == 59:
            cancel_unfilled_orders()
        elif now.hour == 9 and now.minute == 0:  # 수정된 조건
            owned_coins = upbit.get_balances()
            for coin in owned_coins:
                ticker = f"KRW-{coin['currency']}"
                ohlcv = pyupbit.get_ohlcv(ticker, interval="day", count=2)               
                purchase_price = coin['avg_buy_price']  # 평균 매입 가격
                current_price = ohlcv['close'][-1]  # 현재 가격 (최근 종가)
                profit_rate = (current_price - float(purchase_price)) / float(purchase_price) * 100  # 수익률 계산            
                if profit_rate < 10:  # 보유종목수익률 < 10%
                    sell_price = ohlcv['close'][-2]  # 전일 종가로 매도
                    upbit.sell_limit_order(ticker, sell_price, coin['balance'])
                elif profit_rate >= 10:
                    pivot = (ohlcv['high'][-1] + ohlcv['low'][-1] + ohlcv['close'][-1]) / 3
                    resistance = pivot * 2 - ohlcv['low'][-1]
                    if coin['balance'] * resistance > 5000:  # 최소 주문 금액 고려
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
    
    # 설정된 시간 범위: 오전 8시 55분부터 오전 9시 5분까지
    start_time = now.replace(hour=8, minute=55, second=0, microsecond=0)
    end_time = now.replace(hour=9, minute=5, second=0, microsecond=0)
    
    # 현재 시간이 설정된 시간 범위 내인지 확인
    if start_time <= now <= end_time:
        return True
    else:
        return False

if __name__ == "__main__":
    while True:
        if is_time_to_execute():
            print("Executing trade logic")
            # 여기에 작업 로직 함수를 호출합니다. 예: trade()
        else:
            print("현재 시간은 설정된 작업 시간 범위 밖입니다.")
        
        # 1분 대기
        time.sleep(60)
