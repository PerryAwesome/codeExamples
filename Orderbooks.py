import numpy as np
import requests
from MARKETS import markets

class OrderBooks:
    def __init__(self):
        self.orders = {'USD': {True: {1: None}}}
        self.limit_orders = {}

        self.last_updated = 0

    def ratio(self, market, depth=10):
        obk_bids = sorted(self.orders[market][True].items())
        obk_bids.reverse()
        obk_asks = sorted(self.orders[market][False].items())

        bids_sum = sum([v for k, v in obk_bids[:depth]])
        asks_sum = sum([v for k, v in obk_asks[:depth]])
        try:
            return (bids_sum-asks_sum)/(bids_sum+asks_sum)
        except:
            return 0

    def ratio_single_level(self, market, level=1):
        obk_bids = sorted(self.orders[market][True].items())
        obk_bids.reverse()
        obk_asks = sorted(self.orders[market][False].items())

        bids_sum = obk_bids[level][1]
        asks_sum = obk_asks[level][1]
        try:
            return (bids_sum-asks_sum)/(bids_sum+asks_sum)
        except:
            return 0

    def spread(self, market):
        return ((self.ask(market)/self.bid(market))- 1) * 10000


    def bid_depth(self, market, depth):
        try:
            return list(self.orders[market][True].keys())[depth]
        except:
            return np.nan

    def ask_depth(self, market, depth):
        try:
            return list(self.orders[market][False].keys())[depth]
        except:
            return np.nan
    def mid(self, market):
        return (self.bid(market)+self.ask(market))/2

    def bid(self, market):
        try:
            return max(self.orders[market][True].keys())
        except:
            return np.nan

    def worst_bid(self, market):
        try:
            return min(self.orders[market][True].keys())
        except:
            return np.nan

    def estimate_slippage(self, market, size):
        current_size = 0
        if size > 0:
            current_price = self.ask(market)
            obk = sorted(self.orders[market][False].items())
            for k, v in obk:
                current_size += v
                if current_size >= size:
                    break
        else:
            current_price = self.bid(market)
            obk = sorted(self.orders[market][True].items())
            obk.reverse()

            for k, v in obk:
                current_size += v
                if current_size >= abs(size):
                    break
        es = ((k/current_price)-1)*10000
        return es, k

    def size2distance(self, market, size, midprice):
        current_size = size
        if current_size > 0:
            obk = sorted(self.orders[market][False].items())
            for k, v in obk:
                current_size -= v
                if current_size <= 0:
                    break
            return (k - midprice)
        else:
            obk = sorted(self.orders[market][True].items())
            obk.reverse()

            for k, v in obk:
                current_size += v
                if current_size >= 0:
                    break
            return (k-midprice)


    def barrier_thickness(self, market, distance, midprice):
        current_size = 0
        if distance > 0:

            obk = sorted(self.orders[market][False].items())
            for k, v in obk:
                current_size += v
                if k >= midprice + distance*markets[market]['priceIncrement']:
                    break
        else:
            obk = sorted(self.orders[market][True].items())
            obk.reverse()
            for k, v in obk:
                current_size += v
                if k <= midprice + distance*markets[market]['priceIncrement']:
                    break
        return current_size

    def ask(self, market):
        try:
            return min(self.orders[market][False].keys())
        except:
            return np.nan

    def worst_ask(self, market):
        try:
            return max(self.orders[market][False].keys())
        except:
            return np.nan

    def update_limit_orderbook(self, isbid, limit, quantity, market):
        if quantity == 0:
            try:
                del self.limit_orders[market][isbid][limit]
            except:
                pass
        else:
            if market not in self.limit_orders.keys():
                self.limit_orders[market] = {True:{}, False:{}}
            self.limit_orders[market][isbid][limit] = quantity

    def update_order(self, isbid, price, quantity, market):
        if market not in self.orders:
            re = requests.get('https://api.binance.com/api/v3/depth?symbol={}&limit=1000'.format(market.upper())).json()
            self.orders[market] = {True: {}, False: {}}
            for p, s in re['bids']:
                self.orders[market][True][float(p)] = float(s)
            for p, s in re['asks']:
                self.orders[market][False][float(p)] = float(s)

        if quantity == 0:
            try:
                del self.orders[market][isbid][price]
            except:
                pass
        else:
            if market not in self.orders.keys():
                self.orders[market] = {True:{}, False:{}}
            self.orders[market][isbid][price] = quantity

    def flush(self, market):
        try:
            del self.orders[market]
        except:
            pass
        try:
            del self.limit_orders[market]
        except:
            pass


    def new_ticker_data(self, live_ticker):
        for bid_order in live_ticker['data']['b']:
            self.update_order(isbid=True, price=float(bid_order[0]), quantity=float(bid_order[1]), market=live_ticker['data']['s'].lower())
        for ask_order in live_ticker['data']['a']:
            self.update_order(isbid=False, price=float(ask_order[0]), quantity=float(ask_order[1]), market=live_ticker['data']['s'].lower())
