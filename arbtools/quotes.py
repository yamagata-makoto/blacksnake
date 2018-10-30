from functools import reduce
from arbtools.balances import Balances
from arbtools.tradeplan import TradePlan


class Quotes:

    def __init__(self, api, obj):

        self._api = api
        self._data = {}
        self._errors = {}

        if hasattr(obj, '_errors') and isinstance(obj._errors, dict):
            self._errors = obj._errors

        if hasattr(obj, '_data') and isinstance(obj._data, dict):
            for key, data in obj._data.items():
                ask = data['asks'][0]
                bid = data['bids'][~0]
                self._data[key] = { 'ask': ask, 'bid': bid }
        else:
            self._data = obj

    def has_error(self):

        return len(self._errors) > 0

    def errors(self):

        return self._errors

    def items(self):

        return self._data.items()

    def __getitem__(self, name):

        return self._data[name]

    def __contains__(self, name):

        return name in self._data

