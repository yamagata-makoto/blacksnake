import datetime
from functools import partial, reduce


def nop(api, status, next_state, **kwargs):

    return None

def execute_order(api, status, next_state, **kwargs):

    current_state, data = status

    if not 'timestamp' in data:
        data['timestamp'] = datetime.datetime.now()

    ordered = data['orders'] if 'orders' in data else None 
    orders = api.create_orders(data, ordered)
    for exchange_name, result in orders.items():
        if isinstance(result, Exception):
            next_state = current_state
            break

    return (next_state, { 'orders': orders, **data })

def confirm_order(api, status, next_state, **kwargs):

    current_state, data = status
    ordered = data['orders'] if 'orders' in data else None 
    orders = api.fetch_orders(data, ordered)

    def _count_closed(acc, item):
        name, order = item
        if isinstance(order, Exception):
            return acc
        return acc + (order['status'] == 'closed')

    data['orders'] = orders
    if reduce(_count_closed, orders.items(), 0) < 2:
        next_state = current_state

    return (next_state, data)

def close_pair(api, status, next_state, **kwargs):

    current_state, data = status
    broker = kwargs['broker']
    quotes = kwargs['quotes']

    def _reverse_order(broker, data):
        # 反対売買を計画する
        buy = data['sell']['exchange_name']
        sell = data['buy']['exchange_name']
        volume = data['volume']
        plan = broker.specified(quotes, buy, sell, volume)
        result = None
        if plan:
            result = {
                'open_deal': data,
                **plan.deal() 
            }
        return result


    result = _reverse_order(broker, data)
    if not result:
        return status

    broker.emit('reverse_planned', result)

    new_status = status
    def can_reverse_trade(result):
        # 許容されるexitcost以下なら反対売買OK
        allowed_exitcost = result['open_deal']['allowed_exitcost']
        expected_profit = result['expected_profit']
        return (allowed_exitcost+expected_profit) >= 0

    if can_reverse_trade(result):
        rev_status = (current_state, result)
        new_status = execute_order(api, rev_status, next_state)

    return new_status

def finish_trade(api, status, next_state, **kwargs):

    return None

class TradeRule:

    rule = {
        'open_pair': partial(execute_order, next_state='confirm_open'),
        'confirm_open': partial(confirm_order, next_state='close_pair'),
        'close_pair': partial(close_pair, next_state='confirm_close'),
        'confirm_close': partial(confirm_order, next_state='finish_trade'),
        'finish_trade': partial(finish_trade, next_state=None),
    }

    def __init__(self, broker):

        self._broker = broker

    def validate_plan(self, plan):

        is_valid = False

        buy = plan.best('buy')
        sell = plan.best('sell')
        vol = plan.target_volume()
        if all([buy, sell, vol]):
            self._broker.emit('planned', plan)
            if buy['exchange_name'] != sell['exchange_name']:
                is_valid = True

        return is_valid

    def is_ready(self):
        # 未完了のオープン注文があるか？
        reply = True
        status_list = [ status for status, _ in self._requests]
        if 'open_pair' in status_list or 'confirm_open' in status_list:
            reply = False
        return reply

    def validate_quotes(self, quotes):

        if quotes.has_error():
            self._broker.emit('quote_error', quotes.errors())
        return quotes

    def new_status(self, data):

        self._broker.emit('found_open', data)
        return ('open_pair', data)

    def execute(self, status, quotes):

        api = self._broker._api
        status_name, _ = status

        f = self.rule[status_name]
        new_status = f(api, status, broker=self._broker, quotes=quotes)

        if status_name == 'confirm_open':
            if new_status[0] == 'close_pair':
                self._broker.emit('open_pair', new_status[1])

        if status_name == 'close_pair':
            if new_status[0] == 'confirm_close':
                self._broker.emit('found_close', new_status[1])

        if status_name == 'confirm_close':
            if new_status[0] == 'finish_trade':
                self._broker.emit('close_pair', new_status[1])

        return new_status


