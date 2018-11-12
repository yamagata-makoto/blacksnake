import os
import yaml


class Property:

    def __init__(self, data):
        self._data = data

    def items(self):
        for k, v in self._data.items():
            v = Property(v) if isinstance(v, dict) else v
            yield k, v

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def __getattr__(self, key):
        val = self._data[key] if key in self._data.keys() else None
        if isinstance(val, dict):
            val = Property(val)
        return val

    def __getitem__(self, key):
        return self.__getattr__(key)

class Config:

    def __init__(self, filename='config.yaml'):
        with open(filename) as f:
            self._params = Property(yaml.load(f))

    def __getattr__(self, key):

        return getattr(self._params, key)

    def exchange_fees(self):

        return { k: v.fees for k, v in self._params.exchanges.items() }

def load(filename=None):

    def default_filepath():
        dirname = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirname, 'config.yaml')

    filename = filename if filename else default_filepath()

    return Config(filename)

if __name__ == '__main__':
    config = load()
    print(config.trade.trade_volume)

