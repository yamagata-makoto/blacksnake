import unittest
from unittest.mock import MagicMock, patch
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
        
        with patch.object(notificator, '_post_message') as mock_post:
            with patch.object(notificator, '_format_open', return_value='formatted message') as mock_format:
                result = notificator.post_message('open_pair', {'data': 'test'})
                mock_format.assert_called_once_with({'data': 'test'})
                mock_post.assert_called_once_with('\nformatted message')
                self.assertEqual(result, 'formatted message')
        
        with patch.object(notificator, '_post_message') as mock_post:
            data = {'data': 'test'}
            result = notificator.post_message('unknown_event', data)
            mock_post.assert_called_once_with('\n' + str(data))
            self.assertEqual(result, data)

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
        notificator = LINENotificator(self.config)
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            notificator.post_message('open_pair', {'data': 'test'})
            
            mock_post.assert_called()

class TestSlackNotificator(unittest.TestCase):
    """Test cases for the SlackNotificator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.slack.webhook_url = 'https://slack.example.com'

    def test_post_message_behavior(self):
        """Test Slack notificator post_message behavior."""
        notificator = SlackNotificator(self.config)
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            notificator.post_message('open_pair', {'data': 'test'})
            
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
        with patch('notificators.LINENotificator') as mock_line:
            with patch('notificators.SlackNotificator') as mock_slack:
                notificator = MutimediaNotificator(self.config)
                self.assertEqual(len(notificator._notificators), 2)
                mock_line.assert_called_once_with(self.config)
                mock_slack.assert_called_once_with(self.config)

    def test_broadcast_message(self):
        """Test broadcast_message method."""
        mock_line = MagicMock()
        mock_slack = MagicMock()
        
        with patch('notificators.LINENotificator', return_value=mock_line):
            with patch('notificators.SlackNotificator', return_value=mock_slack):
                notificator = MutimediaNotificator(self.config)
                
                notificator.broadcast_message('test_event', {'data': 'test'})
                
                mock_line.post_message.assert_called_once_with('test_event', {'data': 'test'})
                mock_slack.post_message.assert_called_once_with('test_event', {'data': 'test'})

if __name__ == '__main__':
    unittest.main()
