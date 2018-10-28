from functools import reduce

class Positions:
    
    def __init__(self, api, balances, quotes):
        
        self._api = api
        def _position(acc, name):
            if name in balances:
                balance = balances[name]
                quote = quotes[name]
                status = (quote['ask'] is not None, quote['bid'] is not None)
                acc[name] = (balance, status)
            return acc
        self._data = reduce(_position, self._api.names(), {})

    def sum(self, coin):

        def _f(item):
            name, value, = item
            balance, _ = value
            return balance[coin]['free']

        return sum(map(_f, self._data.items()))
        
    def net_exposure(self):

        return self.sum('BTC')
        

    def net_funds(self):

        return self.sum('JPY')


    def items(self):

        return self._data.items()

