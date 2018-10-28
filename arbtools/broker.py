import pickle
from collections import defaultdict
from functools import reduce, partial
from arbtools.balances import Balances
from arbtools.orderbooks import OrderBooks
from arbtools.nothing import Nothing
from arbtools.tradeplan import TradePlan
from arbtools.traderule import TradeRule


class Broker:

    def __init__(self, api, trade):

        self._api = api
        self._trade = trade
        self._listeners = defaultdict(lambda x: x)
        self._requests = []
        self._trade_rule = TradeRule(self)

    def trade_volume(self):

        return self._trade.volume

    def on(self, name, f, **kwargs):

        self._listeners[name] = partial(f, **kwargs) if kwargs else f

        return self

    def emit(self, name, arg):

        return self._listeners[name](self, arg)

    def _to_investments(self, quotes, trade_volume):

        def _investment(acc, item):
            name, quote = item
            price, ask_volume  = quote['ask']
            volume = min([ask_volume, trade_volume])
            price = price * volume 
            fees = self._api[name].trading_fees
            cost = price * (fees / 100.0)
            acc[name] = (price + cost)
            return acc

        return reduce(_investment, quotes.items(), {})

    def _tradable(self, volume, quotes, balances):

        investments = self._to_investments(quotes, volume)

        def _long_OK(name, quote):

            if not name in balances:
                return False

            _, quote_volume = quote
            return all([
                quote_volume > volume,
                balances[name]['JPY']['free'] > investments[name]
            ])

        def _short_OK(name, quote):

            if not name in balances:
                return False

            _, quote_volume = quote
            return all([
                quote_volume > volume,
                balances[name]['BTC']['free'] > volume 
            ])

        def _verify(acc, item):
            name, quote = item
            acc[name] = {
                'ask': quote['ask'] if _long_OK(name, quote['ask']) else None,
                'bid': quote['bid'] if _short_OK(name, quote['bid']) else None,
            }
            return acc
        
        return reduce(_verify, quotes.items(), {})

    def orderbooks(self):

        return OrderBooks(self._api)

    def planning(self, quotes):

        volume = self.trade_volume()
        balances = Balances(self._api)
        quotes_ = self._tradable(volume, quotes, balances)

        plan = TradePlan(self._api, volume, quotes_, balances)
        if not self._trade_rule.validate_plan(plan):
            return Nothing() 

        return plan

    def specified(self, quotes, buy, sell, volume):

        quotes_ = {
            buy: {
                'bid': None,
                'ask': quotes[buy]['ask'],
            },
            sell: {
                'bid': quotes[sell]['bid'],
                'ask': None,
            }
        }
        plan = TradePlan(self._api, volume, quotes_, Balances(self._api))

        return plan
        
    def request(self, deal):

        if isinstance(deal, Nothing):
            return Nothing()

        if deal['profit_rate'] < self._trade.target_profit_rate:
            return Nothing()

        status = self._trade_rule.new_status(deal)
        self._requests.append(status)

        return self

    def process_requests(self):

        new_requests = []
        while self._requests:
            status = self._requests.pop(0)
            next_status = self._trade_rule.execute(status)
            if next_status:
                new_requests.append(next_status)
        self._requests = new_requests

        return self

    def save_to(self, file_name):

        with open(file_name, 'wb') as f:
            pickle.dump(self._requests, f)

        return self

    def load_from(self, file_name):

        try:
            with open(file_name, 'rb') as f:
                self._requests = pickle.load(f) 
        except:
            pass

        return self

    def map_requests(self, f):
        xs = [ f(status) for status in self._requests ]
        return xs

