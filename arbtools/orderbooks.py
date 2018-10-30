import copy
from math import ceil, floor
from functools import partial
from operator import itemgetter
from itertools import groupby
from arbtools.quotes import Quotes


class OrderBooks:

    def __init__(self, api, data=None):

        self._api = api

        items = (data if data else api.fetch_orderbooks()).items()
        self._errors = { k: v for k, v in items if not isinstance(v, dict) }
        self._data = { k: v for k, v in items if k not in self._errors }

    def round(self, price_unit=100):

        def _round_price(prices, round_func, price_unit):

            def stepped(price_steps, values):
                price, volume = values
                return [round_func(price/price_unit) * price_unit, volume]

            price_stepper = partial(stepped, price_unit)
            orders = sorted(list(map(price_stepper, prices)), key=itemgetter(0))
            result = [] 
            for price, grouper in groupby(orders, key=itemgetter(0)):
                result.append((price, sum(volume for _, volume in grouper)))

            return result

        result = {}
        for key, data in self._data.items():
            asks = _round_price(data['asks'], ceil, price_unit)
            bids = _round_price(data['bids'], floor, price_unit)
            result[key] = { 'asks': asks[:100], 'bids': bids[~100:] }

        return OrderBooks(self._api, result)

    def quotes(self):

        return Quotes(self._api, self)

