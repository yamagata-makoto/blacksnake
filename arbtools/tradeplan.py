import uuid
from collections import defaultdict
from functools import reduce
from arbtools.positions import Positions


class TradePlan:

    def __init__(self, api, volume, quotes, balances):

        self._api = api
        self._quotes = quotes
        self._balances = balances
        self._allowed_exitcost_ratio = 50

        def _best(acc, item):

            buy = acc['buy']
            sell = acc['sell']
            vol = acc['volume'] or volume 

            exchange_name, quote = item

            ask = quote['ask']
            bid = quote['bid']

            if ask and ((not buy) or buy['quote'] > ask):
                buy = { 'exchange_name': exchange_name, 'quote': ask }
                vol = min(vol, ask[1])

            if bid and ((not sell) or sell['quote'] < bid):
                sell = { 'exchange_name': exchange_name, 'quote': bid }
                vol = min(vol, bid[1])
            
            return { 'buy': buy, 'sell': sell, 'volume': vol }

        self._deal = reduce(_best, quotes.items(), defaultdict(lambda: None))


    def set_allowed_exitcost_ratio(self, ratio):
        
        self._allowed_exitcost_ratio = ratio

    def best(self, side):

        side = 'buy' if side in ('buy', 'ask') else 'sell'

        return self._deal[side]

    def target_volume(self):

        return self._deal['volume']

    def available_volume(self):

        return min(self._deal[side]['quote'][1] for side in ('buy', 'sell'))

    def spread(self):

        buy_price, _ = self._deal['buy']['quote']
        sell_price, _ = self._deal['sell']['quote']

        return buy_price - sell_price

    def volumed_spread(self, volume=None):

        return self.spread() * (volume if volume else self.target_volume())

    def trade_cost(self):

        volume = self.target_volume()

        def _to_cost(side):

            name = self._deal[side]['exchange_name']
            price, _ = self._deal[side]['quote']

            return (price * volume) * (self._api[name].trading_fees / 100.0)

        return sum(map(_to_cost, ['buy', 'sell']))

    def expected_profit(self):

        profit = -(self.volumed_spread() + self.trade_cost())
        buy_price, _ = self._deal['buy']['quote']
        invest = buy_price * self.target_volume()

        rate = (profit / invest) * 100.0

        return (profit, rate)

    def positions(self):

        return Positions(self._api, self._balances, self._quotes)

    def deal(self):

        allowed_exitcost_rate = self._allowed_exitcost_ratio / 100.0 

        profit, rate = self.expected_profit()
        allowed_exitcost = profit * allowed_exitcost_rate 
        if profit < 0:
            allowed_exitcost = -(profit * (1.0/allowed_exitcost_rate))
        return {
            'deal_id': uuid.uuid4().hex,
            'expected_profit': profit,
            'profit_rate': rate,
            'allowed_exitcost': allowed_exitcost,
            **self._deal,
        }
