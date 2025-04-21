import traceback
import importlib
from collections import defaultdict
from functools import reduce
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from typing import Dict, List, Callable, Any, Optional, Set, Tuple, Iterator

class APIFacade:
    """
    Unified interface to multiple cryptocurrency exchanges.
    
    This class provides a consistent API for interacting with multiple exchanges,
    abstracting away the differences between exchange APIs.
    """

    def __init__(self, exchanges: Dict[str, Any], gw_name: str) -> None:
        """
        Initialize the APIFacade with exchange configurations.
        
        Args:
            exchanges: Dictionary of exchange configurations
            gw_name: Name of the gateway module to import
        """
        self._product: str = 'BTC/JPY'
        self._gw = importlib.import_module(gw_name)

        def _new(name: str, value: Any) -> Tuple[str, Any]:
            """
            Create a new exchange API instance.
            
            Args:
                name: Exchange name
                value: Exchange configuration
                
            Returns:
                Tuple of exchange name and API instance
            """
            klass = getattr(self._gw, name)
            options = { # normalize options
                'apiKey': value.apikey,
                'secret': value.secret,
                'verbose': False,
            }
            instance = klass(options)
            setattr(instance, 'trading_fees', value.fees)
            return (name, instance)

        items = exchanges.items()
        self._api: Dict[str, Any] = dict(_new(k, v) for k, v in items if v.enable)

    def names(self) -> List[str]:
        """
        Get the names of all enabled exchanges.
        
        Returns:
            List of exchange names
        """
        return list(self.keys())

    def keys(self) -> List[str]:
        """
        Get the keys of all enabled exchanges.
        
        Returns:
            List of exchange keys
        """
        return list(self._api.keys())

    def items(self) -> List[Tuple[str, Any]]:
        """
        Get the items (name, API) of all enabled exchanges.
        
        Returns:
            List of (name, API) tuples
        """
        return list(self._api.items())

    def __getitem__(self, exchange_name: str) -> Any:
        """
        Get the API instance for the specified exchange.
        
        Args:
            exchange_name: Name of the exchange
            
        Returns:
            Exchange API instance
        """
        return self._api[exchange_name]

    def traverse(self, f: Callable, *, max_workers: int = 8, allowed_none: bool = False) -> Dict[str, Any]:
        """
        Execute a function across all exchanges in parallel.
        
        Args:
            f: Function to execute for each exchange
            max_workers: Maximum number of parallel workers
            allowed_none: Whether to include None results
            
        Returns:
            Dictionary of results by exchange name
        """
        result: Dict[str, Any] = defaultdict(dict)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(f, (k, v)): k for k, v in self._api.items()}
            for future in as_completed(futures):
                exchange_name = futures[future]
                data = future.result()
                if allowed_none or data:
                    result[exchange_name] = data
        return result

    def fetch_orderbooks(self) -> Dict[str, Any]:
        """
        Fetch order books from all enabled exchanges.
        
        Returns:
            Dictionary of order books by exchange name
        """
        def _fetch(item: Tuple[str, Any]) -> Dict[str, Any]:
            """Fetch order book from a single exchange."""
            _, api = item
            try:
                result = api.fetch_order_book(self._product)
            except Exception as e:
                print(f"Error fetching orderbook: {e}")
                result = { 'fetch_orderbooks_error': str(e) }
            return result

        return self.traverse(_fetch)

    def fetch_balances(self) -> Dict[str, Any]:
        """
        Fetch account balances from all enabled exchanges.
        
        Returns:
            Dictionary of balances by exchange name
        """
        def _fetch(item: Tuple[str, Any]) -> Dict[str, Any]:
            """Fetch balance from a single exchange."""
            _, api = item
            try:
                balance = api.fetch_balance()
                result = { key: balance[key] for key in ['JPY', 'BTC'] }
            except Exception as e:
                print(f"Error fetching balance: {e}")
                result = { 'fetch_balances_error': str(e) }
            return result

        return self.traverse(_fetch)

    def _create_orders_params(self, data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Create parameters for order creation.
        
        Args:
            data: Trade data containing order information
            
        Returns:
            Dictionary of order parameters by exchange name
        """
        def _params(acc: Dict[str, Dict[str, Any]], side: str) -> Dict[str, Dict[str, Any]]:
            """Build order parameters for a single side (buy/sell)."""
            order = data[side]
            exchange_name = order['exchange_name']
            volume = data['volume']
            price = order['quote'][0]
            args = {
                'symbol': 'BTC/JPY',
                'type': 'limit',
                'side': side,
                'amount': volume,
                'price': price
            }
            acc[exchange_name] = args
            return acc

        return reduce(_params, ['buy', 'sell'], {})

    def create_orders(self, data: Dict[str, Any], ordered: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create orders on exchanges based on trade data.
        
        Args:
            data: Trade data containing order information
            ordered: Previously created orders, if any
            
        Returns:
            Dictionary of created orders by exchange name
        """
        params = self._create_orders_params(data)

        def _execute(item: Tuple[str, Any]) -> Optional[Dict[str, Any]]:
            """Execute order creation for a single exchange."""
            name, api = item
            if not name in params:
                return None
            args = params[name]
            try:
                if ordered and (name in ordered) and ('id' in ordered[name]):
                    result = ordered[name]
                else:
                    result = api.create_order(**args)
            except Exception as e:
                print(f"Error creating order: {e}")
                result = { 'create_orders_error': str(e) }
            return result

        return self.traverse(_execute)

    def fetch_orders(self, data: Dict[str, Any], ordered: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch order status from exchanges.
        
        Args:
            data: Trade data containing order information
            ordered: Previously created orders
            
        Returns:
            Dictionary of order status by exchange name
        """
        api = self._api

        def _execute(name: str, order: Dict[str, Any]) -> Dict[str, Any]:
            """Fetch order status for a single exchange."""
            if (name in ordered) and ('status' in ordered[name]):
                if ordered[name]['status'] == 'closed':
                    return ordered[name]
            id_ = order['id']
            return api[name].fetch_order(id_, self._product)

        result: Dict[str, Dict[str, Any]] = defaultdict(dict)
        with ThreadPoolExecutor(max_workers=2) as executor:
            orders = data['orders']
            futures = {executor.submit(_execute, k, v): k for k, v in orders.items()}
            for future in as_completed(futures):
                exchange_name = futures[future]
                try:
                    result[exchange_name] = future.result()
                except Exception as e:
                    print(f"Error fetching order: {e}")
                    result[exchange_name]['id'] = ordered[exchange_name]['id']
                    result[exchange_name]['fetch_orders_error'] = str(e)

        return result
