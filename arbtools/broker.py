import pickle
from collections import defaultdict
from functools import reduce, partial
from typing import Dict, List, Callable, Any, Optional, Set, Tuple
from arbtools.balances import Balances
from arbtools.orderbooks import OrderBooks
from arbtools.nothing import Nothing
from arbtools.tradeplan import TradePlan
from arbtools.traderule import TradeRule


class Broker:
    """
    Central trade orchestrator that manages trade planning and execution.
    """

    def __init__(self, api: Any, trade: Any) -> None:
        """
        Initialize the Broker with API facade and trade configuration.
        
        Args:
            api: API facade for exchange communication
            trade: Trade configuration parameters
        """
        self._api = api
        self._trade = trade
        self._listeners: Dict[str, Callable] = defaultdict(lambda: lambda *args, **kwargs: None)
        self._requests: List[Tuple[str, Dict[str, Any]]] = []
        self._trade_rule = TradeRule(self)
        self._last_quotes: Optional[Dict[str, Any]] = None
        self._last_balances: Optional[Balances] = None

    def trade_volume(self) -> float:
        """
        Get the configured trade volume.
        
        Returns:
            The trade volume from configuration
        """
        return self._trade.volume

    def on(self, name: str, f: Callable, **kwargs) -> 'Broker':
        """
        Register an event listener for the specified event name.
        
        Args:
            name: Event name to listen for
            f: Callback function to execute when event occurs
            **kwargs: Additional arguments to pass to the callback
            
        Returns:
            Self for method chaining
        """
        self._listeners[name] = partial(f, **kwargs) if kwargs else f

        return self

    def emit(self, name: str, arg: Any) -> Any:
        """
        Emit an event with the specified name and argument.
        
        Args:
            name: Event name to emit
            arg: Argument to pass to the event listener
            
        Returns:
            Result of the event listener
        """
        return self._listeners[name](self, arg)

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

    def planning(self, quotes, *, balances=None):

        self._last_quotes = quotes

        volume = self.trade_volume()
        balances = balances if balances else Balances(self._api)
        if balances.has_error():
            return Nothing()

        self._last_balances = balances

        quotes_ = self._tradable(volume, quotes, balances)

        plan = TradePlan(self._api, volume, quotes_, balances)
        plan.set_allowed_exitcost_ratio(self._trade.allowed_exitcost_ratio)
        if not self._trade_rule.validate_plan(plan):
            return Nothing()

        return plan

    def specified(self, quotes, buy, sell, volume, *, balances=None):

        quotes = quotes if quotes else self._last_quotes
        
        if not quotes or not all([buy in quotes, sell in quotes]):
            return None
            
        buy_ask = quotes.get(buy, {}).get('ask')
        sell_bid = quotes.get(sell, {}).get('bid')
        
        if not buy_ask or not sell_bid:
            return None
            
        quotes_ = {
            buy: {
                'bid': None,
                'ask': buy_ask,
            },
            sell: {
                'bid': sell_bid,
                'ask': None,
            }
        }
        balances = balances if balances else Balances(self._api)
        plan = TradePlan(self._api, volume, quotes_, balances)
        plan.set_allowed_exitcost_ratio(self._trade.allowed_exitcost_ratio)

        return plan if plan.target_volume() == volume else None

    def request_is_ready(self):
        # 未完了のオープン注文があるか？
        reply = True
        status_list = [ status for status, _ in self._requests]
        if 'open_pair' in status_list or 'confirm_open' in status_list:
            reply = False
        return reply

    def unclosed_exchanges(self):
        # 未完了のオープン注文がある取引所
        exchanges = []
        for status, deal in self._requests:
            if not status in ('open_pair', 'confirm_open'):
                continue
            for name, param in deal['orders'].items():
                if 'status' in param and param['status'] == 'closed':
                    continue
                exchanges.append(name)
        return set(exchanges)

    def exchange_pair(self, deal):

        return set(deal[side]['exchange_name'] for side in ['buy', 'sell'])

    def request(self, deal):

        if self.unclosed_exchanges() & self.exchange_pair(deal):
            # 未完了のオープン注文がある場合、新規にリクエストを積まない
            return Nothing()

        if len(self._requests) >= self._trade.max_order:
            return Nothing()

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
            next_status = self._trade_rule.execute(
                status, self._last_quotes, self._last_balances)
            if next_status:
                new_requests.append(next_status)
        self._requests = new_requests

        return self
