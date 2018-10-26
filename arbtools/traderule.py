import datetime
from functools import partial, reduce
from arbtools.orderbooks import OrderBooks


def _create_orders_params(data):

    def _params(acc, side):
        order = data[side]
        exchange_name = order['exchange_name']
        volume = data['volume']
        price = order['quote'][0]
        params = {
            'symbol': 'BTC/JPY',
            'type': 'limit',
            'side': side,
            'amount': volume,
            'price': price
        }
        acc[exchange_name] = params
        return acc

    return reduce(_params, ['buy', 'sell'], {})
    
def _create_orders(api, data):

    params = _create_orders_params(data)

    def _execute(name):
        args = params[name]
        if ('orders' in data) and (name in data['orders']):
            order = data['orders'][name]
            if not isinstance(order, Exception):
                return data['orders'][name]
        return api[name].create_order(**args)

    result = {}
    with ThreadPoolExecutor(max_workers=2) as _:
        futures = { _.submit(_execute, name): name for name in api }
        for future in as_completed(futures):
            exchange_name = futures[future]
            try:
                result[exchange_name] = future.result()
            except Exception as e:
                result[exchange_name] = e

    return result

def _fetch_orders(api, data):

    def _execute(name, order):
        id_ = order['id']
        return api[name].fetch_order(id_)

    result = {}
    with ThreadPoolExecutor(max_workers=2) as _:
        orders = data['orders']
        futures = { _.submit(_execute, k, v): k for k, v in orders.items() }
        for future in as_completed(futures):
            exchange_name = futures[future]
            try:
                result[exchange_name] = future.result()
            except Exception as e:
                result[exchange_name] = e

    return result


def nop(api, status, next_state, **kwargs):

    return None

def execute_order(api, status, next_state, **kwargs):

    current_state, data = status

    if not 'timestamp' in data:
        data['timestamp'] = datetime.datetime.now()

    orders = _create_orders(api, data)
    for exchange_name, result in orders.items():
        if isinstance(result, Exception):
            next_state = current_state
            break

    return (next_state, { 'orders': orders, **data })

def confirm_order(api, status, next_state, **kwargs):

    current_state, data = status
    orders = _fetch_order(api, data)

    def _count_closed(acc, item):
        name, order = item
        return acc + (order['status'] == 'closed')

    if reduce(_count_closed, orders.items(), 0) < 2:
        next_state = current_state
    else:
        data['orders'] = orders

    return (next_state, data)

def close_pair(api, status, next_state, **kwargs):

    def _reverse_order(broker, data):

        # 反対売買を計画する
        quotes = broker.orderbooks().round().quotes()
        buy = data['sell']['exchange_name']
        sell = data['buy']['exchange_name']
        volume = data['volume']
        plan = broker.specified(quotes, buy, sell, volume)

        allowed_exitcost = status['allowed_exitcost'] 
        result = {
            'open_deal': data,
            **plan.deal() 
        }
        return result

    current_state, data = status
    broker = kwargs['broker']

    result = _reverse_order(broker, data)
    broker.emit('lookup_close', result)

    # 許容されるexitcost以下なら反対売買を実行
    new_status = status
    def can_reverse_trade(result):
        allowed_exitcost = result['open_deal']['allowed_exitcost']
        expected_profit = result['expected_profit']
        return (allowed_exitcost+expected_profit) >= 0

    if can_reverse_trade(result):
        rev_status = (current_state, result)
        new_status = execute_order(api, rev_status, next_satate)

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

        buy = plan.best('buy')
        sell = plan.best('sell')
        vol = plan.target_volume()
        is_valid = False
        if all([buy, sell, vol, buy['exchange_name']!=sell['exchange_name']]):
            self._broker.emit('planned', plan)
            is_valid = True
        return is_valid

    def new_status(self, data):

        self.emit('found_open', data)
        return ('open_pair', data)

    def execute(self, api, status):

        status_name, _ = status

        f = self.rule[status_name]
        new_status = f(api, status, broker=self._broker)

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


