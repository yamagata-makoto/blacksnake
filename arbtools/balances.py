
class Balances:

    def __init__(self, api):

        self._api = api
        items = api.fetch_balances().items()
        self._errors = { k: v for k, v in items if isinstance(v, Exception) }
        self._data = { k: v for k, v in items if k not in self._errors }

    def __getitem__(self, name):

        return self._data[name]

    def __contains__(self, name):
        
        return name in self._data

