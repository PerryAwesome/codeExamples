import Model
from MARKETS import markets
import numpy as np

class Model_14(Model.Model):
    """
    MM
    Avellaneda Stoikov, 2008
    https://www.math.nyu.edu/~avellane/HighFrequencyTrading.pdf

    Tickerbasiert
    """

    def __init__(self):
        super().__init__()
        self.market = 'BTC-PERP'
        self.pf.add_market(self.market)
        self.last_ticker[self.market] = {'bid': None, 'ask': None, 'last': None, 'last_updated': 0}

        self.interval_start = 0
        self.t = 0
        self.parameters = {'Timespan': 600,
                           'γ': 0.005,
                           'target_inventory': 0,
                           'update_interval': 0.7}

        self.total_fills = 0

        self.up = None
        self.down = None
        print(self.parameters)
        self.last_fills = 0

    def check_signal(self, ticker):
        if ticker['type'] == 'update' and ticker['market'] == self.market:
            fills, triggers = super().check_signal(ticker)

            if fills:
                self.total_fills += 1

            self.last_ticker[self.market]['last_updated'] = ticker['data']['time']
            self.last_ticker[self.market]['bid'] = ticker['data']['bid']
            self.last_ticker[self.market]['ask'] = ticker['data']['ask']
            self.last_ticker[self.market]['last'] = ticker['data']['last']

            if ticker['data']['time'] > self.t + self.parameters['update_interval']:
                self.t = ticker['data']['time']
                if self.interval_start == 0 or self.t > self.interval_start+self.parameters['Timespan']:
                    self.interval_start = ticker['data']['time']

                self.pf.cancel_all_orders()

                balance = self.balance()
                if self.balance() == 0:
                    print('GG WP')
                    return

                Qa = ticker['data']['askSize']
                Qb = ticker['data']['bidSize']
                I = Qb / (Qb + Qa)
                mid = ticker['data']['bid'] * (1 - I) + ticker['data']['ask'] * I

                q = ((self.pf.portfolio[self.market]*ticker['data']['last'])-(self.parameters['target_inventory']*ticker['data']['last']))/self.balance()
                Tt = (self.interval_start+self.parameters['Timespan']-self.t)/self.parameters['Timespan']
                #Tt = 1
                σ = 2
                κ = 26

                drift = q*self.parameters['γ']*(σ**2)*Tt * (ticker['data']['last']/100)
                reservation_price = mid - drift


                optimal_spread = self.parameters['γ']*(σ**2)*Tt + (2/self.parameters['γ'])*np.log(1+(self.parameters['γ']/κ)) * (ticker['data']['last']/100)

                bid_offer_price = reservation_price - optimal_spread / 2
                ask_offer_price = reservation_price + optimal_spread / 2

                self.down = self.round_to_increment(bid_offer_price, increment=markets[self.market]['priceIncrement'])
                self.up = self.round_to_increment(ask_offer_price, increment=markets[self.market]['priceIncrement'])

                if self.last_fills != self.total_fills:
                    self.last_fills = self.total_fills
                    print(self.last_ticker)
                    print(self.parameters)
                    print('q: {:.6f}/{:.6f}    Tt: {:4f}    σ: {:.6f}     κ: {:.6f}    DRIFT: {:.6f}    SPREAD: {:.6f}    Total fills: {}    pnl: {:.2f}$\n'.format(q, self.pf.portfolio[self.market], Tt, σ, κ, drift, optimal_spread, self.total_fills, balance-100))


                self.pf.new_limit_order(side='buy', price=self.down, size=markets[self.market]['sizeIncrement'], market=self.market)
                self.pf.new_limit_order(side='sell', price=self.up, size=markets[self.market]['sizeIncrement'], market=self.market)


            return fills, triggers, self.up, self.down
        else:
            return [], [], None, None