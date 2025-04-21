import datetime
from functools import partial, reduce
from typing import Dict, List, Callable, Any, Optional, Tuple, Union


JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')

def nop(api: Any, status: Tuple[str, Dict[str, Any]], next_state: Optional[str], **kwargs) -> None:
    """
    No-operation function for the state machine.
    
    Args:
        api: API facade for exchange communication
        status: Current state and data tuple
        next_state: Next state to transition to
        **kwargs: Additional arguments
        
    Returns:
        None to indicate no state transition
    """
    return None

def execute_order(api: Any, status: Tuple[str, Dict[str, Any]], next_state: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
    """
    Execute orders for the current trade state.
    
    Args:
        api: API facade for exchange communication
        status: Current state and data tuple
        next_state: Next state to transition to
        **kwargs: Additional arguments
        
    Returns:
        Tuple of next state and updated data
    """
    current_state, data = status

    if not 'timestamp' in data:
        data['timestamp'] = datetime.datetime.now(JST)

    ordered = data['orders'] if 'orders' in data else None
    orders = api.create_orders(data, ordered)

    def _count_open(acc: int, item: Tuple[str, Dict[str, Any]]) -> int:
        """Count the number of successfully opened orders."""
        name, result = item
        if 'id' not in result:
            return acc
        return acc + 1

    if reduce(_count_open, orders.items(), 0) < 2:
        next_state = current_state

    return (next_state, { 'orders': orders, **data })

def confirm_order(api: Any, status: Tuple[str, Dict[str, Any]], next_state: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
    """
    Confirm order status for the current trade state.
    
    Args:
        api: API facade for exchange communication
        status: Current state and data tuple
        next_state: Next state to transition to
        **kwargs: Additional arguments including broker reference
        
    Returns:
        Tuple of next state and updated data
    """
    broker = kwargs['broker']

    current_state, data = status
    ordered = data['orders'] if 'orders' in data else None
    orders = api.fetch_orders(data, ordered)

    def _count_closed(acc: int, item: Tuple[str, Dict[str, Any]]) -> int:
        """Count the number of closed orders."""
        name, order = item
        if not 'status' in order:
            return acc
        return acc + (order['status'] == 'closed')

    data['orders'] = orders
    broker.emit('confirm_order', data)
    if reduce(_count_closed, orders.items(), 0) < 2:
        next_state = current_state

    return (next_state, data)

def close_pair(api: Any, status: Tuple[str, Dict[str, Any]], next_state: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
    """
    Close a trading pair by planning and executing a reverse trade.
    
    Args:
        api: API facade for exchange communication
        status: Current state and data tuple
        next_state: Next state to transition to
        **kwargs: Additional arguments including broker, quotes, and balances
        
    Returns:
        Tuple of next state and updated data
    """
    current_state, data = status
    broker = kwargs['broker']
    quotes = kwargs['quotes']
    balances = kwargs['balances']

    def _reverse_order(broker: Any, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Plan a reverse trade to close the position.
        
        Args:
            broker: Broker instance to use for planning
            data: Current trade data
            
        Returns:
            Planned reverse trade data or None if planning fails
        """
        # 反対売買を計画する (Plan a reverse trade)
        buy = data['sell']['exchange_name']
        sell = data['buy']['exchange_name']
        volume = data['volume']
        plan = broker.specified(quotes, buy, sell, volume, balances=balances)
        result = None
        if plan:
            result = {
                'open_deal': data,
                **plan.deal()
            }
        return result

    result = _reverse_order(broker, data)
    broker.emit('reverse_planned', result)
    if not result:
        return status

    new_status = status
    def can_reverse_trade(result: Dict[str, Any]) -> bool:
        """
        Check if the reverse trade is acceptable based on exit cost.
        
        Args:
            result: Planned reverse trade data
            
        Returns:
            True if the reverse trade is acceptable, False otherwise
        """
        # 許容されるexitcost以下なら反対売買OK (Reverse trade is OK if exit cost is below allowed threshold)
        allowed_exitcost = result['open_deal']['allowed_exitcost']
        expected_profit = result['expected_profit']
        return (allowed_exitcost+expected_profit) >= 0

    if can_reverse_trade(result):
        rev_status = (current_state, result)
        new_status = execute_order(api, rev_status, next_state)

    return new_status

def finish_trade(api: Any, status: Tuple[str, Dict[str, Any]], next_state: Optional[str], **kwargs) -> None:
    """
    Finish a trade and clean up resources.
    
    Args:
        api: API facade for exchange communication
        status: Current state and data tuple
        next_state: Next state to transition to
        **kwargs: Additional arguments
        
    Returns:
        None to indicate the trade is complete
    """
    return None

class TradeRule:
    """
    State machine implementation for trading workflow.
    
    This class manages the state transitions for the trading process,
    from opening positions to closing them and finalizing trades.
    """

    rule: Dict[str, Callable] = {
        'open_pair': partial(execute_order, next_state='confirm_open'),
        'confirm_open': partial(confirm_order, next_state='close_pair'),
        'close_pair': partial(close_pair, next_state='confirm_close'),
        'confirm_close': partial(confirm_order, next_state='finish_trade'),
        'finish_trade': partial(finish_trade, next_state=None),
    }

    def __init__(self, broker: Any) -> None:
        """
        Initialize the TradeRule with a broker instance.
        
        Args:
            broker: Broker instance to use for trade execution
        """
        self._broker = broker

    def validate_plan(self, plan: Any) -> bool:
        """
        Validate a trade plan to ensure it meets trading criteria.
        
        Args:
            plan: TradePlan instance to validate
            
        Returns:
            True if the plan is valid, False otherwise
        """
        if plan._balances.has_error():
            self._broker.emit('balance_error', plan._balances.errors())

        is_valid = False
        buy = plan.best('buy')
        sell = plan.best('sell')
        vol = plan.target_volume()
        if all([buy, sell, vol]):
            self._broker.emit('planned', plan)
            if buy['exchange_name'] != sell['exchange_name']:
                is_valid = True

        return is_valid

    def new_status(self, data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Create a new trade status for the given data.
        
        Args:
            data: Trade data to create status for
            
        Returns:
            Tuple of initial state and data
        """
        self._broker.emit('found_open', data)
        return ('open_pair', data)

    def execute(self, status: Tuple[str, Dict[str, Any]], quotes: Dict[str, Any], balances: Any) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Execute the state machine for the current trade status.
        
        Args:
            status: Current state and data tuple
            quotes: Current market quotes
            balances: Current account balances
            
        Returns:
            Tuple of next state and updated data, or None if the trade is complete
        """
        api = self._broker._api
        status_name, _ = status

        f = self.rule[status_name]
        args = {
            'broker': self._broker,
            'quotes': quotes,
            'balances': balances,
        }
        new_status = f(api, status, **args)

        if status_name == 'confirm_open':
            if new_status and new_status[0] == 'close_pair':
                self._broker.emit('open_pair', new_status[1])

        if status_name == 'close_pair':
            if new_status and new_status[0] == 'confirm_close':
                self._broker.emit('found_close', new_status[1])

        if status_name == 'confirm_close':
            if new_status and new_status[0] == 'finish_trade':
                self._broker.emit('close_pair', new_status[1])

        return new_status
