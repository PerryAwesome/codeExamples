import Model
from MARKETS import markets
import numpy as np

class Model_15(Model.Model):
    """
    MM
    Order Size unterschied statt drift
    http://stanford.edu/class/msande448/2018/Final/Reports/gr5.pdf

    Ticker- und Orderbookbasiert
    """

    def __init__(self, parameters = None):
        super().__init__()
        self.market = 'BTC-PERP'
        self.pf.add_market(self.market)
        self.last_ticker[self.market] = {'bid': None, 'ask': None, 'last': None, 'last_updated': 0}

        self.interval_start = 0
        self.t = 0
        if parameters is None:
            self.parameters = {'target_inventory': 0,
                               'max_inventory': 100,
                               'update_interval': 1,
                               'default_spread': 12,
                               'φ_max': 10,
                               'η': -2}
        else:
            self.parameters = parameters

        self.total_fills = 0

        self.up = None
        self.down = None
        print(self.parameters)
        self.last_fills = 0

    def check_signal(self, ticker):
        try:
            if ticker['channel'] == 'orderbook':
                self.ob.new_ticker_data(ticker)
                return [], [], None, None

            elif ticker['type'] == 'update' and ticker['market'] == self.market and ticker['channel'] == 'ticker' and self.market in self.ob.orders:
                fills, triggers = super().check_signal(ticker)

                if fills:
                    self.total_fills += 1

                self.last_ticker[self.market]['last_updated'] = ticker['data']['time']
                self.last_ticker[self.market]['bid'] = ticker['data']['bid']
                self.last_ticker[self.market]['ask'] = ticker['data']['ask']
                self.last_ticker[self.market]['last'] = ticker['data']['last']

                if ticker['data']['time'] > self.t + self.parameters['update_interval']:
                    self.t = ticker['data']['time']

                    self.pf.cancel_all_orders()

                    balance = self.balance()
                    if self.balance() == 0:
                        print('GG WP')
                        return

                    Qa = ticker['data']['askSize']
                    Qb = ticker['data']['bidSize']
                    I = Qb / (Qb + Qa)
                    mid = ticker['data']['bid'] * (1 - I) + ticker['data']['ask'] * I


                    q = (self.pf.portfolio[self.market]/markets[self.market]['sizeIncrement'])/self.parameters['max_inventory']
                    φ_bid = self.parameters['φ_max'] if q < 0 else self.parameters['φ_max'] * np.exp(q*self.parameters['η'])
                    φ_ask = self.parameters['φ_max'] if q > 0 else self.parameters['φ_max'] * np.exp(abs(q) * self.parameters['η'])

                    distance_bid = -self.parameters['default_spread']*markets[self.market]['priceIncrement']
                    distance_ask = self.parameters['default_spread']*markets[self.market]['priceIncrement']

                    bid_offer_price = mid + distance_bid
                    ask_offer_price = mid + distance_ask

                    self.down = self.round_to_increment(bid_offer_price, increment=markets[self.market]['priceIncrement'])
                    self.up = self.round_to_increment(ask_offer_price, increment=markets[self.market]['priceIncrement'])

                    bid_size = self.round_to_increment(round(φ_bid), increment=markets[self.market]['sizeIncrement'])* markets[self.market]['sizeIncrement']
                    ask_size = self.round_to_increment(round(φ_ask), increment=markets[self.market]['sizeIncrement'])* markets[self.market]['sizeIncrement']

                    if self.last_fills != self.total_fills:
                        self.last_fills = self.total_fills
                        print('q: {:.6f}/{:.6f}    φ_bid: {:4f}/{:4f}    φ_ask: {:4f}/{:4f}    distance_ask: {:.6f}    distance_bid: {:.6f}    Total fills: {}    pnl: {:.2f}$\n'.format(q, self.pf.portfolio[self.market], φ_bid,bid_size, φ_ask, ask_size, distance_ask, distance_bid, self.total_fills, balance-100))



                    self.pf.new_limit_order(side='buy', price=self.down, size=bid_size, market=self.market)
                    self.pf.new_limit_order(side='sell', price=self.up, size=ask_size, market=self.market)


                return fills, triggers, self.up, self.down
            else:
                return [], [], None, None
        except Exception as e:
            print(e)
            return [], [], None, None