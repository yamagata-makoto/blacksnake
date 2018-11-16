import traceback
import importlib
from collections import defaultdict
from functools import reduce
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

class APIFacade:

    def __init__(self, exchanges, gw_name):

        self._product = 'BTC/JPY'
        self._gw = importlib.import_module(gw_name)

        def _new(name, value):

            klass = getattr(self._gw, name)
            options = { # normalize options
                'apiKey': value.apikey,
                'secret': value.secret,
                'verbose': False,
            }
            instance = klass(options)
            setattr(instance, 'trading_fees', value.fees)
            return (name, instance)

        items = exchanges.items()
        self._api = dict(_new(k, v) for k, v in items if v.enable)

    def names(self):

        return self.keys()

    def keys(self):

        return self._api.keys()

    def items(self):

        return self._api.items()

    def __getitem__(self, exchange_name):

        return self._api[exchange_name]

    def traverse(self, f, *, max_workers=8, allowed_none=False):

        result = defaultdict(dict)
        with ThreadPoolExecutor(max_workers=max_workers) as _:
            futures = { _.submit(f, (k, v)): k for k, v in self._api.items() }
            for future in as_completed(futures):
                exchange_name = futures[future]
                data = future.result()
                if allowed_none or data:
                    result[exchange_name] = data
        return result

    def fetch_orderbooks(self):

        def _fetch(item):
            _, api = item
            try:
                result = api.fetch_order_book(self._product)
            except Exception as e:
                print(e)
                result = { 'fetch_orderbooks_error': e }
            return result

        return self.traverse(_fetch)

    def fetch_balances(self):

        def _fetch(item):
            _, api = item
            try:
                balance = api.fetch_balance()
                result = { key: balance[key] for key in ['JPY', 'BTC'] }
            except Exception as e:
                print(e)
                result = { 'fetch_balances_error': e }
            return result

        return self.traverse(_fetch)

    def _create_orders_params(self, data):

        def _params(acc, side):
            order = data[side]
            exchange_name = order['exchange_name']
            volume = data['volume']
            price = order['quote'][0]
            args = {
                'symbol': 'BTC/JPY',
                'type': 'limit',
                'side': side,
                'amount': volume,
                'price': price
            }
            acc[exchange_name] = args
            return acc

        return reduce(_params, ['buy', 'sell'], {})

    def create_orders(self, data, ordered):

        params = self._create_orders_params(data)

        def _execute(item):
            name, api = item
            if not name in params:
                return None
            args = params[name]
            try:
                if ordered and (name in ordered) and ('id' in ordered[name]):
                    result = ordered[name]
                else:
                    result = api.create_order(**args)
            except Exception as e:
                result = { 'create_orders_error': e }
            return result

        return self.traverse(_execute)

    def fetch_orders(self, data, ordered):

        api = self._api

        def _execute(name, order):
            if (name in ordered) and ('status' in ordered[name]):
                if ordered[name]['status'] == 'closed':
                    return ordered[name]
            id_ = order['id']
            return api[name].fetch_order(id_, self._product)

        result = defaultdict(dict)
        with ThreadPoolExecutor(max_workers=2) as _:
            orders = data['orders']
            futures = { _.submit(_execute, k, v): k for k, v in orders.items() }
            for future in as_completed(futures):
                exchange_name = futures[future]
                try:
                    result[exchange_name] = future.result()
                except Exception as e:
                    result[exchange_name]['id'] = ordered[exchange_name]['id']
                    result[exchange_name]['fetch_orders_error'] = e

        return result
