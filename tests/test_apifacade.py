import unittest
from unittest.mock import MagicMock, patch
from collections import defaultdict
from arbtools.apifacade import APIFacade

class TestAPIFacade(unittest.TestCase):
    """Test cases for the APIFacade class."""

    def setUp(self):
        """Set up test fixtures."""
        self.exchange_config = {
            'exchange1': MagicMock(enable=True, apikey='key1', secret='secret1'),
            'exchange2': MagicMock(enable=True, apikey='key2', secret='secret2'),
            'exchange3': MagicMock(enable=False, apikey='key3', secret='secret3')
        }
        
        self.mock_gw = MagicMock()
        self.mock_exchange1 = MagicMock()
        self.mock_exchange2 = MagicMock()
        
        with patch.dict('sys.modules', {'test_gw': self.mock_gw}):
            self.mock_gw.exchange1 = MagicMock(return_value=self.mock_exchange1)
            self.mock_gw.exchange2 = MagicMock(return_value=self.mock_exchange2)
            
            self.api_facade = APIFacade(self.exchange_config, 'test_gw')

    def test_init(self):
        """Test APIFacade initialization."""
        self.assertEqual(len(self.api_facade._api), 2)
        self.assertIn('exchange1', self.api_facade._api)
        self.assertIn('exchange2', self.api_facade._api)
        self.assertNotIn('exchange3', self.api_facade._api)
        
        self.assertEqual(self.api_facade._product, 'BTC/JPY')

    def test_names_and_keys(self):
        """Test names and keys methods."""
        self.assertEqual(set(self.api_facade.names()), {'exchange1', 'exchange2'})
        self.assertEqual(set(self.api_facade.keys()), {'exchange1', 'exchange2'})

    def test_items(self):
        """Test items method."""
        items = self.api_facade.items()
        self.assertEqual(len(items), 2)
        self.assertEqual({item[0] for item in items}, {'exchange1', 'exchange2'})

    def test_getitem(self):
        """Test __getitem__ method."""
        self.assertEqual(self.api_facade['exchange1'], self.mock_exchange1)
        self.assertEqual(self.api_facade['exchange2'], self.mock_exchange2)
        
        with self.assertRaises(KeyError):
            _ = self.api_facade['exchange3']

    def test_traverse(self):
        """Test traverse method."""
        def test_func(item):
            name, api = item
            return f"Processed {name}"
        
        result = self.api_facade.traverse(test_func)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result['exchange1'], "Processed exchange1")
        self.assertEqual(result['exchange2'], "Processed exchange2")

    def test_fetch_orderbooks(self):
        """Test fetch_orderbooks method."""
        self.mock_exchange1.fetch_order_book.return_value = {'bids': [[100, 1]], 'asks': [[101, 1]]}
        self.mock_exchange2.fetch_order_book.return_value = {'bids': [[99, 1]], 'asks': [[102, 1]]}
        
        result = self.api_facade.fetch_orderbooks()
        
        self.mock_exchange1.fetch_order_book.assert_called_once_with('BTC/JPY')
        self.mock_exchange2.fetch_order_book.assert_called_once_with('BTC/JPY')
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result['exchange1']['bids'], [[100, 1]])
        self.assertEqual(result['exchange2']['asks'], [[102, 1]])

    def test_fetch_orderbooks_error_handling(self):
        """Test fetch_orderbooks error handling."""
        self.mock_exchange1.fetch_order_book.side_effect = Exception("Test error")
        
        result = self.api_facade.fetch_orderbooks()
        
        self.assertIn('fetch_orderbooks_error', result['exchange1'])
        self.assertEqual(result['exchange1']['fetch_orderbooks_error'], "Test error")

    def test_fetch_balances(self):
        """Test fetch_balances method."""
        self.mock_exchange1.fetch_balance.return_value = {'JPY': 100000, 'BTC': 1.0}
        self.mock_exchange2.fetch_balance.return_value = {'JPY': 200000, 'BTC': 2.0}
        
        result = self.api_facade.fetch_balances()
        
        self.mock_exchange1.fetch_balance.assert_called_once()
        self.mock_exchange2.fetch_balance.assert_called_once()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result['exchange1']['JPY'], 100000)
        self.assertEqual(result['exchange1']['BTC'], 1.0)
        self.assertEqual(result['exchange2']['JPY'], 200000)
        self.assertEqual(result['exchange2']['BTC'], 2.0)

    def test_fetch_balances_error_handling(self):
        """Test fetch_balances error handling."""
        self.mock_exchange1.fetch_balance.side_effect = Exception("Test error")
        
        result = self.api_facade.fetch_balances()
        
        self.assertIn('fetch_balances_error', result['exchange1'])
        self.assertEqual(result['exchange1']['fetch_balances_error'], "Test error")

    def test_create_orders_params(self):
        """Test _create_orders_params method."""
        data = {
            'buy': {
                'exchange_name': 'exchange1',
                'price': 100,
                'side': 'buy'
            },
            'sell': {
                'exchange_name': 'exchange2',
                'price': 101,
                'side': 'sell'
            },
            'volume': 0.01
        }
        
        result = self.api_facade._create_orders_params(data)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result['exchange1']['symbol'], 'BTC/JPY')
        self.assertEqual(result['exchange1']['type'], 'limit')
        self.assertEqual(result['exchange1']['side'], 'buy')
        self.assertEqual(result['exchange1']['amount'], 0.01)
        self.assertEqual(result['exchange1']['price'], 100)
        
        self.assertEqual(result['exchange2']['symbol'], 'BTC/JPY')
        self.assertEqual(result['exchange2']['type'], 'limit')
        self.assertEqual(result['exchange2']['side'], 'sell')
        self.assertEqual(result['exchange2']['amount'], 0.01)
        self.assertEqual(result['exchange2']['price'], 101)

if __name__ == '__main__':
    unittest.main()
