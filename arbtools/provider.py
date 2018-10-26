import importlib
from functools import reduce
from arbtools.orderbooks import OrderBooks
from arbtools.broker import Broker

class Provider:

    def __init__(self, exchanges, gw_name='ccxt'):

        self._api = {}
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

    def orderbooks(self):

        return OrderBooks(self._api)

    def broker(self, trade):
        
        return Broker(self._api, trade)

