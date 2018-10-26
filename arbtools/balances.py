from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed


class Balances:

    def __init__(self, api):

        self._api = api
        items = self._fetch_balances().items()
        self._errors = { k: v for k, v in items if isinstance(v, Exception) }
        self._data = { k: v for k, v in items if k not in self._errors }

    def _fetch_balances(self):

        def _fetch(api):

            balance = api.fetch_balance()
            return { key: balance[key] for key in ['JPY', 'BTC'] }

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


    def __getitem__(self, name):

        return self._data[name]

