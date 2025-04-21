import unittest
from unittest.mock import MagicMock, patch
import pickle
from collections import defaultdict
from arbtools.broker import Broker
from arbtools.nothing import Nothing

class TestBroker(unittest.TestCase):
    """Test cases for the Broker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.api = MagicMock()
        self.trade = MagicMock()
        self.trade.volume = 0.01
        self.broker = Broker(self.api, self.trade)

    def test_init(self):
        """Test broker initialization."""
        self.assertEqual(self.broker._api, self.api)
        self.assertEqual(self.broker._trade, self.trade)
        self.assertIsInstance(self.broker._listeners, defaultdict)
        self.assertEqual(self.broker._requests, [])
        self.assertIsNone(self.broker._last_quotes)
        self.assertIsNone(self.broker._last_balances)

    def test_trade_volume(self):
        """Test trade_volume method returns correct volume."""
        self.assertEqual(self.broker.trade_volume(), 0.01)

    def test_on_method(self):
        """Test on method registers event listeners correctly."""
        callback = MagicMock()
        self.broker.on('test_event', callback)
        
        self.assertEqual(self.broker._listeners['test_event'], callback)
        
        self.broker.on('test_event_with_kwargs', callback, param='value')
        self.broker._listeners['test_event_with_kwargs'](self.broker, 'arg')
        callback.assert_called_with(self.broker, 'arg', param='value')

    def test_emit_method(self):
        """Test emit method calls registered listeners."""
        callback = MagicMock()
        self.broker.on('test_event', callback)
        self.broker.emit('test_event', 'test_arg')
        callback.assert_called_once_with(self.broker, 'test_arg')

    def test_defaultdict_implementation(self):
        """Test that the defaultdict implementation works correctly."""
        result = self.broker._listeners['non_existent_event'](self.broker, 'arg')
        self.assertIsNone(result)  # Should return None and not raise an error

    def test_specified_with_none_quotes(self):
        """Test specified method handles None quotes correctly."""
        result = self.broker.specified(None, 'buy_exchange', 'sell_exchange', 0.01)
        self.assertIsNone(result)
        
        quotes = {
            'buy_exchange': {'ask': 100, 'bid': 99},
            'sell_exchange': {'ask': 102, 'bid': 101}
        }
        self.broker._last_quotes = quotes
        result = self.broker.specified(None, 'buy_exchange', 'sell_exchange', 0.01)
        self.assertIsNotNone(result)

    def test_specified_with_invalid_exchanges(self):
        """Test specified method handles invalid exchanges correctly."""
        quotes = {
            'buy_exchange': {'ask': 100, 'bid': 99},
            'sell_exchange': {'ask': 102, 'bid': 101}
        }
        result = self.broker.specified(quotes, 'invalid_exchange', 'sell_exchange', 0.01)
        self.assertIsNone(result)
        
        result = self.broker.specified(quotes, 'buy_exchange', 'invalid_exchange', 0.01)
        self.assertIsNone(result)

    def test_save_and_load(self):
        """Test save_to and load_from methods."""
        mock_open = MagicMock()
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch('builtins.open', mock_open):
            with patch('pickle.dump') as mock_dump:
                self.broker.save_to('test_file.pcl')
                mock_dump.assert_called_once()
            
            with patch('pickle.load', return_value=[]) as mock_load:
                self.broker.load_from('test_file.pcl')
                mock_load.assert_called_once()

if __name__ == '__main__':
    unittest.main()
