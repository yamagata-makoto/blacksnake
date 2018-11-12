from functools import reduce
from arbtools.orderbooks import OrderBooks
from arbtools.broker import Broker
from arbtools.apifacade import APIFacade

class Provider:

    def __init__(self, exchanges, gw_name='ccxt'):

        self._api = APIFacade(exchanges, gw_name)

    def orderbooks(self):

        return OrderBooks(self._api)

    def broker(self, trade):

        return Broker(self._api, trade)

