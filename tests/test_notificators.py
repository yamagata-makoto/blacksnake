import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from notificators import Notificator, LINENotificator, SlackNotificator, MutimediaNotificator

class TestNotificator(unittest.TestCase):
    """Test cases for the Notificator base class."""

    def test_init(self):
        """Test notificator initialization."""
        notificator = Notificator()
        self.assertIsInstance(notificator._formatter, dict)
        self.assertIn('found_open', notificator._formatter)
        self.assertIn('open_pair', notificator._formatter)
        self.assertIn('found_close', notificator._formatter)
        self.assertIn('close_pair', notificator._formatter)

    def test_post_message(self):
        """Test post_message method."""
        notificator = Notificator()
        
        test_data = {
            'buy': {'exchange_name': 'exchange1', 'quote': [100, 1.0]},
            'sell': {'exchange_name': 'exchange2', 'quote': [105, 1.0]},
            'volume': 0.01,
            'expected_profit': 50,
            'allowed_exitcost': 25,
            'deal_id': '12345'
        }
        
        with patch.object(notificator, '_post_message') as mock_post:
            with patch.dict(notificator._formatter, {'open_pair': MagicMock(return_value='formatted message')}):
                result = notificator.post_message('open_pair', test_data)
                notificator._formatter['open_pair'].assert_called_once_with(test_data)
                mock_post.assert_called_once_with('\nformatted message')
                self.assertEqual(result, 'formatted message')
        
        with patch.object(notificator, '_post_message') as mock_post:
            result = notificator.post_message('unknown_event', test_data)
            mock_post.assert_called_once_with('\n' + str(test_data))
            self.assertEqual(result, str(test_data))

    def test_abstract_post_message(self):
        """Test that _post_message raises NotImplementedError."""
        notificator = Notificator()
        with self.assertRaises(NotImplementedError):
            notificator._post_message('test message')

class TestLINENotificator(unittest.TestCase):
    """Test cases for the LINENotificator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.line.url = 'https://line.example.com'
        self.config.line.token = 'test_token'

    def test_post_message_behavior(self):
        """Test LINE notificator post_message behavior."""
        with patch('notificators._format_open', return_value='Formatted message'):
            notificator = LINENotificator(self.config)
            
            with patch('requests.post') as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_post.return_value = mock_response
                
                test_data = {
                    'buy': {'exchange_name': 'exchange1', 'quote': [100, 1.0]},
                    'sell': {'exchange_name': 'exchange2', 'quote': [105, 1.0]},
                    'volume': 0.01,
                    'expected_profit': 50,
                    'allowed_exitcost': 25,
                    'deal_id': '12345'
                }
                
                with patch.object(notificator, '_format_open', return_value='Formatted message'):
                    notificator.post_message('open_pair', test_data)
                    mock_post.assert_called()

class TestSlackNotificator(unittest.TestCase):
    """Test cases for the SlackNotificator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.slack.webhook_url = 'https://slack.example.com'

    def test_post_message_behavior(self):
        """Test Slack notificator post_message behavior."""
        with patch('notificators._format_open', return_value='Formatted message'):
            notificator = SlackNotificator(self.config)
            
            with patch('requests.post') as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_post.return_value = mock_response
                
                test_data = {
                    'buy': {'exchange_name': 'exchange1', 'quote': [100, 1.0]},
                    'sell': {'exchange_name': 'exchange2', 'quote': [105, 1.0]},
                    'volume': 0.01,
                    'expected_profit': 50,
                    'allowed_exitcost': 25,
                    'deal_id': '12345'
                }
                
                with patch.object(notificator, '_format_open', return_value='Formatted message'):
                    notificator.post_message('open_pair', test_data)
                    mock_post.assert_called()

class TestMutimediaNotificator(unittest.TestCase):
    """Test cases for the MutimediaNotificator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.line.enable = True
        self.config.slack.enable = True

    def test_init(self):
        """Test multimedia notificator initialization."""
        self.config.items.return_value = [
            ('line', MagicMock(enable=True)),
            ('slack', MagicMock(enable=True))
        ]
        
        with patch.object(MutimediaNotificator, 'classes', {
            'line': MagicMock(return_value=MagicMock()),
            'slack': MagicMock(return_value=MagicMock())
        }):
            notificator = MutimediaNotificator(self.config)
            self.assertEqual(len(notificator._notificators), 2)

    def test_broadcast_message(self):
        """Test broadcast_message method."""
        mock_line = MagicMock()
        mock_slack = MagicMock()
        
        test_data = {
            'buy': {'exchange_name': 'exchange1', 'quote': [100, 1.0]},
            'sell': {'exchange_name': 'exchange2', 'quote': [105, 1.0]},
            'volume': 0.01,
            'expected_profit': 50,
            'allowed_exitcost': 25,
            'deal_id': '12345'
        }
        
        notificator = MutimediaNotificator(self.config)
        notificator._notificators = {'line': mock_line, 'slack': mock_slack}
        
        notificator.broadcast_message('test_event', test_data)
        
        mock_line.post_message.assert_called_once_with('test_event', test_data)
        mock_slack.post_message.assert_called_once_with('test_event', test_data)

if __name__ == '__main__':
    unittest.main()
