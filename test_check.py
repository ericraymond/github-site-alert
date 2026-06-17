import sys
from unittest.mock import MagicMock

# Mock requests and yaml modules before they are imported by check.py
mock_yaml = MagicMock()
mock_requests = MagicMock()

sys.modules['yaml'] = mock_yaml
sys.modules['requests'] = mock_requests

import os
import json
import unittest
from unittest.mock import patch, mock_open

# Import check
import check

class TestCheckSentinel(unittest.TestCase):
    @patch('check.load_old_products')
    @patch('check.save_current_products')
    @patch('check.load_history_logs')
    @patch('check.save_history_logs')
    def test_sentinel_disappears(self, mock_save_history, mock_load_history, mock_save_products, mock_load_products):
        mock_load_products.return_value = ({"111"}, True, "idle")
        mock_load_history.return_value = []
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "products": [
                {
                    "id": 111,
                    "title": "T-Shirt",
                    "handle": "t-shirt",
                    "body_html": "Cool shirt",
                    "variants": [{"price": "19.99", "available": True}]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_requests.get.reset_mock()
        
        with patch('check.SIGNAL_PHONE', '+15551234567'), patch('check.SIGNAL_API_KEY', 'dummy_key'):
            check.main()
            
        self.assertEqual(mock_requests.get.call_count, 2)
        signal_call = mock_requests.get.call_args_list[1]
        params = signal_call[1]['params']
        self.assertEqual(params['text'], "SNS Starting")
        mock_save_products.assert_called_with({"111"}, False, "sns_active")

    @patch('check.load_old_products')
    @patch('check.save_current_products')
    @patch('check.load_history_logs')
    @patch('check.save_history_logs')
    def test_sentinel_reappears_end_in_sight(self, mock_save_history, mock_load_history, mock_save_products, mock_load_products):
        mock_load_products.return_value = ({"111"}, False, "sns_active")
        mock_load_history.return_value = []
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "products": [
                {
                    "id": 111,
                    "title": "T-Shirt",
                    "handle": "t-shirt",
                    "body_html": "Cool shirt",
                    "variants": [{"price": "19.99", "available": True}]
                },
                {
                    "id": 222,
                    "title": "SUPER STUD awesome vintage shirt",
                    "handle": "super-stud",
                    "body_html": "Cool stud shirt",
                    "variants": [{"price": "30.00", "available": True}]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_requests.get.reset_mock()
        
        with patch('check.SIGNAL_PHONE', '+15551234567'), patch('check.SIGNAL_API_KEY', 'dummy_key'):
            check.main()
            
        self.assertEqual(mock_requests.get.call_count, 2)
        signal_call = mock_requests.get.call_args_list[1]
        params = signal_call[1]['params']
        self.assertIn("End in Sight", params['text'])
        self.assertIn("📦 New Inventory: SUPER STUD awesome vintage shirt listed for ＄30.00.", params['text'])
        mock_save_products.assert_called_with({"111", "222"}, True, "end_in_sight")

    @patch('check.load_old_products')
    @patch('check.save_current_products')
    @patch('check.load_history_logs')
    @patch('check.save_history_logs')
    def test_end_in_sight_to_sns_over(self, mock_save_history, mock_load_history, mock_save_products, mock_load_products):
        mock_load_products.return_value = ({"111", "222"}, True, "end_in_sight")
        mock_load_history.return_value = []
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "products": [
                {
                    "id": 222,
                    "title": "SUPER STUD awesome vintage shirt",
                    "handle": "super-stud",
                    "body_html": "Cool stud shirt",
                    "variants": [{"price": "30.00", "available": True}]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_requests.get.reset_mock()
        
        with patch('check.SIGNAL_PHONE', '+15551234567'), patch('check.SIGNAL_API_KEY', 'dummy_key'):
            check.main()
            
        self.assertEqual(mock_requests.get.call_count, 2)
        signal_call = mock_requests.get.call_args_list[1]
        params = signal_call[1]['params']
        self.assertEqual(params['text'], "SNS Over")
        mock_save_products.assert_called_with({"222"}, True, "idle")

    @patch('check.load_old_products')
    @patch('check.save_current_products')
    @patch('check.load_history_logs')
    @patch('check.save_history_logs')
    def test_sns_active_to_sns_over_directly(self, mock_save_history, mock_load_history, mock_save_products, mock_load_products):
        mock_load_products.return_value = ({"111"}, False, "sns_active")
        mock_load_history.return_value = []
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "products": [
                {
                    "id": 222,
                    "title": "SUPER STUD awesome vintage shirt",
                    "handle": "super-stud",
                    "body_html": "Cool stud shirt",
                    "variants": [{"price": "30.00", "available": True}]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_requests.get.reset_mock()
        
        with patch('check.SIGNAL_PHONE', '+15551234567'), patch('check.SIGNAL_API_KEY', 'dummy_key'):
            check.main()
            
        self.assertEqual(mock_requests.get.call_count, 2)
        signal_call = mock_requests.get.call_args_list[1]
        params = signal_call[1]['params']
        self.assertIn("SNS Over", params['text'])
        mock_save_products.assert_called_with({"222"}, True, "idle")

    @patch('check.load_old_products')
    @patch('check.save_current_products')
    @patch('check.load_history_logs')
    @patch('check.save_history_logs')
    def test_sentinel_fallback_resolution_previously_seen(self, mock_save_history, mock_load_history, mock_save_products, mock_load_products):
        # sentinel_previously_seen is None (fallback from history needed)
        # sentinel is present in logs with id 222, and id 222 is in old_ids (was seen)
        mock_load_products.return_value = ({"111", "222"}, None, None)
        mock_load_history.return_value = [
            {"id": "222", "title": "SUPER STUD awesome vintage shirt", "price": 30.0, "available": True}
        ]
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "products": [
                {
                    "id": 111,
                    "title": "T-Shirt",
                    "handle": "t-shirt",
                    "body_html": "Cool shirt",
                    "variants": [{"price": "19.99", "available": True}]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_requests.get.reset_mock()
        
        with patch('check.SIGNAL_PHONE', '+15551234567'), patch('check.SIGNAL_API_KEY', 'dummy_key'):
            check.main()
            
        # Resolved previously_seen = True, currently_seen = False -> Should send Just Kidding
        self.assertEqual(mock_requests.get.call_count, 2)
        signal_call = mock_requests.get.call_args_list[1]
        params = signal_call[1]['params']
        self.assertEqual(params['text'], "Just Kidding")
        mock_save_products.assert_called_with({"111"}, False, "sns_active")

    @patch('check.load_old_products')
    @patch('check.save_current_products')
    @patch('check.load_history_logs')
    @patch('check.save_history_logs')
    def test_sentinel_fallback_resolution_previously_not_seen(self, mock_save_history, mock_load_history, mock_save_products, mock_load_products):
        # sentinel_previously_seen is None (fallback from history needed)
        # sentinel is present in logs with id 222, but id 222 is NOT in old_ids (was not seen)
        mock_load_products.return_value = ({"111"}, None, None)
        mock_load_history.return_value = [
            {"id": "222", "title": "SUPER STUD awesome vintage shirt", "price": 30.0, "available": True}
        ]
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "products": [
                {
                    "id": 111,
                    "title": "T-Shirt",
                    "handle": "t-shirt",
                    "body_html": "Cool shirt",
                    "variants": [{"price": "19.99", "available": True}]
                },
                {
                    "id": 222,
                    "title": "SUPER STUD awesome vintage shirt",
                    "handle": "super-stud",
                    "body_html": "Cool stud shirt",
                    "variants": [{"price": "30.00", "available": True}]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_requests.get.reset_mock()
        
        with patch('check.SIGNAL_PHONE', '+15551234567'), patch('check.SIGNAL_API_KEY', 'dummy_key'):
            check.main()
            
        # Resolved previously_seen = False, currently_seen = True -> Should send End in Sight
        self.assertEqual(mock_requests.get.call_count, 2)
        signal_call = mock_requests.get.call_args_list[1]
        params = signal_call[1]['params']
        self.assertIn("End in Sight", params['text'])
        mock_save_products.assert_called_with({"111", "222"}, True, "end_in_sight")

    @patch('check.load_old_products')
    @patch('check.save_current_products')
    @patch('check.load_history_logs')
    @patch('check.save_history_logs')
    def test_end_in_sight_to_sns_active_just_kidding(self, mock_save_history, mock_load_history, mock_save_products, mock_load_products):
        mock_load_products.return_value = ({"111", "222"}, True, "end_in_sight")
        mock_load_history.return_value = []
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "products": [
                {
                    "id": 111,
                    "title": "T-Shirt",
                    "handle": "t-shirt",
                    "body_html": "Cool shirt",
                    "variants": [{"price": "19.99", "available": True}]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_requests.get.reset_mock()
        
        with patch('check.SIGNAL_PHONE', '+15551234567'), patch('check.SIGNAL_API_KEY', 'dummy_key'):
            check.main()
            
        self.assertEqual(mock_requests.get.call_count, 2)
        signal_call = mock_requests.get.call_args_list[1]
        params = signal_call[1]['params']
        self.assertEqual(params['text'], "Just Kidding")
        mock_save_products.assert_called_with({"111"}, False, "sns_active")

    @patch('check.load_old_products')
    @patch('check.save_current_products')
    @patch('check.load_history_logs')
    @patch('check.save_history_logs')
    def test_no_transition_idle(self, mock_save_history, mock_load_history, mock_save_products, mock_load_products):
        mock_load_products.return_value = ({"222"}, True, "idle")
        mock_load_history.return_value = []
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "products": [
                {
                    "id": 222,
                    "title": "SUPER STUD awesome vintage shirt",
                    "handle": "super-stud",
                    "body_html": "Cool stud shirt",
                    "variants": [{"price": "30.00", "available": True}]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_requests.get.reset_mock()
        
        with patch('check.SIGNAL_PHONE', '+15551234567'), patch('check.SIGNAL_API_KEY', 'dummy_key'):
            check.main()
            
        # Should only fetch Shopify URL, no Signal alert request
        self.assertEqual(mock_requests.get.call_count, 1)
        mock_save_products.assert_called_with({"222"}, True, "idle")

    @patch('check.load_old_products')
    @patch('check.save_current_products')
    @patch('check.load_history_logs')
    @patch('check.save_history_logs')
    def test_no_transition_sns_active(self, mock_save_history, mock_load_history, mock_save_products, mock_load_products):
        mock_load_products.return_value = ({"111"}, False, "sns_active")
        mock_load_history.return_value = []
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "products": [
                {
                    "id": 111,
                    "title": "T-Shirt",
                    "handle": "t-shirt",
                    "body_html": "Cool shirt",
                    "variants": [{"price": "19.99", "available": True}]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_requests.get.reset_mock()
        
        with patch('check.SIGNAL_PHONE', '+15551234567'), patch('check.SIGNAL_API_KEY', 'dummy_key'):
            check.main()
            
        # Should only fetch Shopify URL, no Signal alert request
        self.assertEqual(mock_requests.get.call_count, 1)
        mock_save_products.assert_called_with({"111"}, False, "sns_active")

    @patch('check.load_old_products')
    @patch('check.save_current_products')
    @patch('check.load_history_logs')
    @patch('check.save_history_logs')
    def test_no_transition_end_in_sight(self, mock_save_history, mock_load_history, mock_save_products, mock_load_products):
        mock_load_products.return_value = ({"111", "222"}, True, "end_in_sight")
        mock_load_history.return_value = []
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "products": [
                {
                    "id": 111,
                    "title": "T-Shirt",
                    "handle": "t-shirt",
                    "body_html": "Cool shirt",
                    "variants": [{"price": "19.99", "available": True}]
                },
                {
                    "id": 222,
                    "title": "SUPER STUD awesome vintage shirt",
                    "handle": "super-stud",
                    "body_html": "Cool stud shirt",
                    "variants": [{"price": "30.00", "available": True}]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_requests.get.reset_mock()
        
        with patch('check.SIGNAL_PHONE', '+15551234567'), patch('check.SIGNAL_API_KEY', 'dummy_key'):
            check.main()
            
        # Should only fetch Shopify URL, no Signal alert request
        self.assertEqual(mock_requests.get.call_count, 1)
        mock_save_products.assert_called_with({"111", "222"}, True, "end_in_sight")

    @patch('check.load_old_products')
    @patch('check.save_current_products')
    @patch('check.load_history_logs')
    @patch('check.save_history_logs')
    def test_price_change_alert(self, mock_save_history, mock_load_history, mock_save_products, mock_load_products):
        mock_load_products.return_value = ({"111"}, False, "sns_active")
        mock_load_history.return_value = [
            {"id": "111", "title": "T-Shirt", "price": 19.99, "available": True}
        ]
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "products": [
                {
                    "id": 111,
                    "title": "T-Shirt",
                    "handle": "t-shirt",
                    "body_html": "Cool shirt",
                    "variants": [{"price": "14.99", "available": True}]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_requests.get.reset_mock()
        
        with patch('check.SIGNAL_PHONE', '+15551234567'), patch('check.SIGNAL_API_KEY', 'dummy_key'):
            check.main()
            
        self.assertEqual(mock_requests.get.call_count, 2)
        signal_call = mock_requests.get.call_args_list[1]
        params = signal_call[1]['params']
        self.assertIn("💰 Price Change: T-Shirt is now ＄14.99 (was ＄19.99).", params['text'])

    @patch('check.load_old_products')
    @patch('check.save_current_products')
    @patch('check.load_history_logs')
    @patch('check.save_history_logs')
    def test_sold_out_alert(self, mock_save_history, mock_load_history, mock_save_products, mock_load_products):
        mock_load_products.return_value = ({"111"}, False, "sns_active")
        mock_load_history.return_value = [
            {"id": "111", "title": "T-Shirt", "price": 19.99, "available": True}
        ]
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "products": [
                {
                    "id": 111,
                    "title": "T-Shirt",
                    "handle": "t-shirt",
                    "body_html": "Cool shirt",
                    "variants": [{"price": "19.99", "available": False}]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_requests.get.reset_mock()
        
        with patch('check.SIGNAL_PHONE', '+15551234567'), patch('check.SIGNAL_API_KEY', 'dummy_key'):
            check.main()
            
        self.assertEqual(mock_requests.get.call_count, 2)
        signal_call = mock_requests.get.call_args_list[1]
        params = signal_call[1]['params']
        self.assertIn("🔴 SOLD OUT: T-Shirt is now sold out.", params['text'])

    @patch('check.load_old_products')
    @patch('check.save_current_products')
    @patch('check.load_history_logs')
    @patch('check.save_history_logs')
    def test_back_in_stock_alert(self, mock_save_history, mock_load_history, mock_save_products, mock_load_products):
        mock_load_products.return_value = ({"111"}, False, "sns_active")
        mock_load_history.return_value = [
            {"id": "111", "title": "T-Shirt", "price": 19.99, "available": False}
        ]
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "products": [
                {
                    "id": 111,
                    "title": "T-Shirt",
                    "handle": "t-shirt",
                    "body_html": "Cool shirt",
                    "variants": [{"price": "19.99", "available": True}]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_requests.get.reset_mock()
        
        with patch('check.SIGNAL_PHONE', '+15551234567'), patch('check.SIGNAL_API_KEY', 'dummy_key'):
            check.main()
            
        self.assertEqual(mock_requests.get.call_count, 2)
        signal_call = mock_requests.get.call_args_list[1]
        params = signal_call[1]['params']
        self.assertIn("🟢 Back in Stock: T-Shirt is now available for ＄19.99!", params['text'])

    @patch('check.load_old_products')
    @patch('check.save_current_products')
    @patch('check.load_history_logs')
    @patch('check.save_history_logs')
    def test_price_and_availability_change_alert(self, mock_save_history, mock_load_history, mock_save_products, mock_load_products):
        mock_load_products.return_value = ({"111"}, False, "sns_active")
        mock_load_history.return_value = [
            {"id": "111", "title": "T-Shirt", "price": 19.99, "available": False}
        ]
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "products": [
                {
                    "id": 111,
                    "title": "T-Shirt",
                    "handle": "t-shirt",
                    "body_html": "Cool shirt",
                    "variants": [{"price": "24.99", "available": True}]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_requests.get.reset_mock()
        
        with patch('check.SIGNAL_PHONE', '+15551234567'), patch('check.SIGNAL_API_KEY', 'dummy_key'):
            check.main()
            
        self.assertEqual(mock_requests.get.call_count, 2)
        signal_call = mock_requests.get.call_args_list[1]
        params = signal_call[1]['params']
        self.assertIn("🟢 Back in Stock: T-Shirt is now available for ＄24.99!", params['text'])
        self.assertIn("💰 Price Change: T-Shirt is now ＄24.99 (was ＄19.99).", params['text'])


class TestLoadSaveState(unittest.TestCase):
    @patch('os.path.exists')
    def test_load_no_file(self, mock_exists):
        mock_exists.return_value = False
        product_ids, sentinel_seen, state = check.load_old_products()
        self.assertEqual(product_ids, set())
        self.assertIsNone(sentinel_seen)
        self.assertIsNone(state)

    @patch('os.path.exists')
    def test_load_list_format(self, mock_exists):
        mock_exists.return_value = True
        read_data = json.dumps(["111", "222"])
        with patch('builtins.open', mock_open(read_data=read_data)):
            product_ids, sentinel_seen, state = check.load_old_products()
        self.assertEqual(product_ids, {"111", "222"})
        self.assertIsNone(sentinel_seen)
        self.assertIsNone(state)

    @patch('os.path.exists')
    def test_load_modern_dict_format(self, mock_exists):
        mock_exists.return_value = True
        read_data = json.dumps({
            "product_ids": ["111", "222"],
            "sentinel_seen": True
        })
        with patch('builtins.open', mock_open(read_data=read_data)):
            product_ids, sentinel_seen, state = check.load_old_products()
        self.assertEqual(product_ids, {"111", "222"})
        self.assertTrue(sentinel_seen)
        self.assertIsNone(state)

    @patch('os.path.exists')
    def test_load_state_dict_format(self, mock_exists):
        mock_exists.return_value = True
        read_data = json.dumps({
            "product_ids": ["111", "222"],
            "sentinel_seen": True,
            "state": "end_in_sight"
        })
        with patch('builtins.open', mock_open(read_data=read_data)):
            product_ids, sentinel_seen, state = check.load_old_products()
        self.assertEqual(product_ids, {"111", "222"})
        self.assertTrue(sentinel_seen)
        self.assertEqual(state, "end_in_sight")

    @patch('os.path.exists')
    def test_load_state_dict_format_sns_active(self, mock_exists):
        mock_exists.return_value = True
        read_data = json.dumps({
            "product_ids": ["111"],
            "sentinel_seen": False,
            "state": "sns_active"
        })
        with patch('builtins.open', mock_open(read_data=read_data)):
            product_ids, sentinel_seen, state = check.load_old_products()
        self.assertEqual(product_ids, {"111"})
        self.assertFalse(sentinel_seen)
        self.assertEqual(state, "sns_active")

    @patch('os.path.exists')
    def test_load_state_dict_format_idle(self, mock_exists):
        mock_exists.return_value = True
        read_data = json.dumps({
            "product_ids": ["222"],
            "sentinel_seen": True,
            "state": "idle"
        })
        with patch('builtins.open', mock_open(read_data=read_data)):
            product_ids, sentinel_seen, state = check.load_old_products()
        self.assertEqual(product_ids, {"222"})
        self.assertTrue(sentinel_seen)
        self.assertEqual(state, "idle")

    @patch('os.path.exists')
    def test_load_legacy_dict_format(self, mock_exists):
        mock_exists.return_value = True
        read_data = json.dumps({
            "product_ids": ["111", "222"],
            "super_stud_seen": True
        })
        with patch('builtins.open', mock_open(read_data=read_data)):
            product_ids, sentinel_seen, state = check.load_old_products()
        self.assertEqual(product_ids, {"111", "222"})
        self.assertTrue(sentinel_seen)
        self.assertIsNone(state)

    def test_save_current_products_end_in_sight(self):
        m = mock_open()
        with patch('builtins.open', m):
            check.save_current_products({"111", "222"}, True, "end_in_sight")
        
        m.assert_called_once_with(check.STATE_FILE, "w")
        handle = m()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        parsed_data = json.loads(written_data)
        
        self.assertEqual(set(parsed_data["product_ids"]), {"111", "222"})
        self.assertTrue(parsed_data["sentinel_seen"])
        self.assertEqual(parsed_data["state"], "end_in_sight")

    def test_save_current_products_sns_active(self):
        m = mock_open()
        with patch('builtins.open', m):
            check.save_current_products({"111"}, False, "sns_active")
        
        m.assert_called_once_with(check.STATE_FILE, "w")
        handle = m()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        parsed_data = json.loads(written_data)
        
        self.assertEqual(set(parsed_data["product_ids"]), {"111"})
        self.assertFalse(parsed_data["sentinel_seen"])
        self.assertEqual(parsed_data["state"], "sns_active")

    def test_save_current_products_idle(self):
        m = mock_open()
        with patch('builtins.open', m):
            check.save_current_products({"222"}, True, "idle")
        
        m.assert_called_once_with(check.STATE_FILE, "w")
        handle = m()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        parsed_data = json.loads(written_data)
        
        self.assertEqual(set(parsed_data["product_ids"]), {"222"})
        self.assertTrue(parsed_data["sentinel_seen"])
        self.assertEqual(parsed_data["state"], "idle")

if __name__ == '__main__':
    unittest.main()
