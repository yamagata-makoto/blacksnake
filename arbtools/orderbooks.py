import copy
from math import ceil, floor
from functools import partial
from operator import itemgetter
from itertools import groupby
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from arbtools.quotes import Quotes


class OrderBooks:

    def __init__(self, api, data=None):

        self._api = api

        items = (data if data else self._fetch_orderbooks('BTC/JPY')).items()
        self._errors = { k: v for k, v in items if isinstance(v, Exception) }
        self._data = { k: v for k, v in items if k not in self._errors }

    def _fetch_orderbooks(self, product):

        def _fetch(api):
            return api.fetch_order_book(product)

        result = {}
        with ThreadPoolExecutor(max_workers=8) as _:
            futures = { _.submit(_fetch, v): k for k, v in self._api.items() }
            for future in as_completed(futures):
                exchange_name = futures[future]
                try:
                    data = future.result()
                    result[exchange_name] = data
                except Exception as e:
                    result[exchange_name] = e
        return result

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

