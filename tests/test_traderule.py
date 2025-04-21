import unittest
from unittest.mock import MagicMock, patch
import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arbtools.traderule import TradeRule, nop, execute_order, confirm_order, close_pair, finish_trade

class TestTradeRuleFunctions(unittest.TestCase):
    """Test cases for the TradeRule helper functions."""

    def test_nop(self):
        """Test nop function returns None."""
        api = MagicMock()
        status = ('test_state', {'data': 'test'})
        next_state = 'next_state'
        
        result = nop(api, status, next_state)
        self.assertIsNone(result)

    def test_execute_order(self):
        """Test execute_order function."""
        api = MagicMock()
        data = {'volume': 0.01}
        status = ('open_pair', data)
        next_state = 'confirm_open'
        
        orders = {
            'exchange1': {'id': 'order1'},
            'exchange2': {'id': 'order2'}
        }
        api.create_orders.return_value = orders
        
        result = execute_order(api, status, next_state)
        
        api.create_orders.assert_called_once_with(data, None)
        
        self.assertEqual(result[0], next_state)
        self.assertEqual(result[1]['orders'], orders)
        self.assertIn('timestamp', result[1])

    def test_confirm_order(self):
        """Test confirm_order function."""
        api = MagicMock()
        broker = MagicMock()
        orders = {
            'exchange1': {'id': 'order1'},
            'exchange2': {'id': 'order2'}
        }
        data = {'orders': orders, 'volume': 0.01}
        status = ('confirm_open', data)
        next_state = 'close_pair'
        
        fetched_orders = {
            'exchange1': {'id': 'order1', 'status': 'closed'},
            'exchange2': {'id': 'order2', 'status': 'closed'}
        }
        api.fetch_orders.return_value = fetched_orders
        
        result = confirm_order(api, status, next_state, broker=broker)
        
        api.fetch_orders.assert_called_once_with(data, orders)
        
        self.assertEqual(result[0], next_state)
        self.assertEqual(result[1], data)

    def test_close_pair(self):
        """Test close_pair function."""
        api = MagicMock()
        broker = MagicMock()
        quotes = MagicMock()
        balances = MagicMock()
        
        data = {
            'buy': {'exchange_name': 'exchange1'},
            'sell': {'exchange_name': 'exchange2'},
            'volume': 0.01,
            'allowed_exitcost': 50  # Add allowed_exitcost to the data
        }
        status = ('close_pair', data)
        next_state = 'confirm_close'
        
        plan = MagicMock()
        plan.expected_profit = 100
        plan.deal.return_value = {
            'expected_profit': 100
        }
        broker.specified.return_value = plan
        
        with patch('arbtools.traderule.execute_order') as mock_execute_order:
            mock_execute_order.return_value = (next_state, {'close': True})
            
            result = close_pair(api, status, next_state, broker=broker, quotes=quotes, balances=balances)
            
            broker.specified.assert_called_once_with(quotes, 'exchange2', 'exchange1', 0.01, balances=balances)
            
            self.assertEqual(result[0], next_state)
            self.assertIn('close', result[1])

    def test_finish_trade(self):
        """Test finish_trade function returns None."""
        api = MagicMock()
        status = ('finish_trade', {'data': 'test'})
        next_state = None
        
        result = finish_trade(api, status, next_state)
        self.assertIsNone(result)

class TestTradeRule(unittest.TestCase):
    """Test cases for the TradeRule class."""

    def setUp(self):
        """Set up test fixtures."""
        self.broker = MagicMock()
        self.trade_rule = TradeRule(self.broker)

    def test_init(self):
        """Test TradeRule initialization."""
        self.assertEqual(self.trade_rule._broker, self.broker)
        self.assertIn('open_pair', self.trade_rule.rule)
        self.assertIn('confirm_open', self.trade_rule.rule)
        self.assertIn('close_pair', self.trade_rule.rule)
        self.assertIn('confirm_close', self.trade_rule.rule)
        self.assertIn('finish_trade', self.trade_rule.rule)

    def test_validate_plan_valid(self):
        """Test validate_plan with a valid plan."""
        plan = MagicMock()
        plan._balances.has_error.return_value = False
        plan.expected_profit = 100
        plan.target_profit = 50
        plan.best.side_effect = lambda side: {'exchange_name': f'{side}_exchange'} if side in ['buy', 'sell'] else None
        plan.target_volume.return_value = 0.01
        
        result = self.trade_rule.validate_plan(plan)
        self.broker.emit.assert_any_call('planned', plan)
        self.assertTrue(result)

    def test_validate_plan_invalid_balance(self):
        """Test validate_plan with invalid balance."""
        plan = MagicMock()
        plan._balances.has_error.return_value = True
        plan._balances.errors.return_value = ['Balance error']
        
        result = self.trade_rule.validate_plan(plan)
        self.assertFalse(result)
        self.broker.emit.assert_any_call('balance_error', ['Balance error'])

    def test_validate_plan_invalid_profit(self):
        """Test validate_plan with invalid profit."""
        plan = MagicMock()
        plan._balances.has_error.return_value = False
        plan.expected_profit = 40
        plan.target_profit = 50
        plan.best.side_effect = lambda side: {'exchange_name': f'{side}_exchange'} if side == 'buy' else None
        plan.target_volume.return_value = 0.01
        
        result = self.trade_rule.validate_plan(plan)
        self.assertFalse(result)

    def test_new_status(self):
        """Test new_status method."""
        data = {'volume': 0.01}
        
        result = self.trade_rule.new_status(data)
        
        self.broker.emit.assert_called_once_with('found_open', data)
        self.assertEqual(result[0], 'open_pair')
        self.assertEqual(result[1], data)

    def test_execute(self):
        """Test execute method."""
        api = MagicMock()
        self.broker._api = api
        
        status = ('open_pair', {'volume': 0.01})
        quotes = {'exchange1': {'ask': [100, 1.0], 'bid': [99, 1.0]}}
        balances = MagicMock()
        
        next_status = ('confirm_open', {'volume': 0.01, 'orders': {}})
        mock_rule = MagicMock(return_value=next_status)
        
        with patch.dict(self.trade_rule.rule, {'open_pair': mock_rule}):
            result = self.trade_rule.execute(status, quotes, balances)
            
            mock_rule.assert_called_once()
            self.assertEqual(result, next_status)

    def test_execute_state_transitions(self):
        """Test execute method state transitions."""
        api = MagicMock()
        self.broker._api = api
        
        status = ('confirm_open', {'volume': 0.01})
        next_status = ('close_pair', {'volume': 0.01})
        
        mock_rule = MagicMock(return_value=next_status)
        
        with patch.dict(self.trade_rule.rule, {'confirm_open': mock_rule}):
            result = self.trade_rule.execute(status, {}, MagicMock())
            mock_rule.assert_called_once()
            self.broker.emit.assert_called_with('open_pair', next_status[1])
            self.assertEqual(result, next_status)
        
        self.broker.reset_mock()
        
        status = ('close_pair', {'volume': 0.01})
        next_status = ('confirm_close', {'volume': 0.01})
        
        mock_rule = MagicMock(return_value=next_status)
        
        with patch.dict(self.trade_rule.rule, {'close_pair': mock_rule}):
            result = self.trade_rule.execute(status, {}, MagicMock())
            mock_rule.assert_called_once()
            self.broker.emit.assert_called_with('found_close', next_status[1])
            self.assertEqual(result, next_status)
        
        self.broker.reset_mock()
        
        status = ('confirm_close', {'volume': 0.01})
        next_status = ('finish_trade', {'volume': 0.01})
        
        mock_rule = MagicMock(return_value=next_status)
        
        with patch.dict(self.trade_rule.rule, {'confirm_close': mock_rule}):
            result = self.trade_rule.execute(status, {}, MagicMock())
            mock_rule.assert_called_once()
            self.broker.emit.assert_called_with('close_pair', next_status[1])
            self.assertEqual(result, next_status)

if __name__ == '__main__':
    unittest.main()
