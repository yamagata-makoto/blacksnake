from functools import reduce
from collections import defaultdict
import requests
import json


def _format_open(data):

    sell = data['sell']
    buy  = data['buy']
    param = (
        buy['exchange_name'],
        sell['exchange_name'],
        buy['quote'][0],
        sell['quote'][0],
        data['volume'],
        buy['quote'][0]*data['volume'],
        data['expected_profit'],
        data['expected_profit']-data['allowed_exitcost'],
        data['deal_id'],
    )
    return "\n".join([
        "<<ポジションオープン>>",
        "[{0:}=>{1:}]",
        "ASK: {2:,.0f}",
        "BID: {3:,.0f}",
        "VOL: {4:}",
        "投下資本: {5:,.0f}円",
        "暫定利益: {6:,.0f}円",
        "想定利益: {7:,.0f}円",
        "取引ID: {8:}"
    ]).format(*param)

def _format_found_open(data):

    sell = data['sell']
    buy  = data['buy']
    param = (
        buy['exchange_name'],
        sell['exchange_name'],
        buy['quote'][0],
        sell['quote'][0],
        data['volume'],
        buy['quote'][0]*data['volume'],
        data['expected_profit'],
        data['expected_profit']-data['allowed_exitcost'],
        data['deal_id'],
    )
    return "\n".join([
        "<<裁定機会検出>>",
        "[{0:}=>{1:}]",
        "ASK: {2:,.0f}",
        "BID: {3:,.0f}",
        "VOL: {4:}",
        "投下資本: {5:,.0f}円",
        "暫定利益: {6:,.0f}円",
        "想定利益: {7:,.0f}円",
        "取引ID:{8:}",
    ]).format(*param)

def _format_found_close(data):
    sell = data['sell']
    buy  = data['buy']
    profit = data['open_deal']['expected_profit'] + data['expected_profit']
    param = (
        buy['exchange_name'],
        sell['exchange_name'],
        buy['quote'][0],
        sell['quote'][0],
        data['volume'],
        data['expected_profit'],
        profit,
        data['deal_id'],
    )
    return "\n".join([
        "<<利確機会検出>>",
        "[{0:}<={1:}]",
        "ASK: {2:,.0f}",
        "BID: {3:,.0f}",
        "VOL: {4:}",
        "利確コスト: {5:,.0f}円",
        "想定利益: {6:,.0f}円",
        "取引ID: {7:}",
    ]).format(*param)

def _format_close(data):
    sell = data['sell']
    buy  = data['buy']
    profit = data['open_deal']['expected_profit'] + data['expected_profit']
    param = (
        buy['exchange_name'],
        sell['exchange_name'],
        buy['quote'][0],
        sell['quote'][0],
        data['volume'],
        profit,
        data['deal_id'],
    )
    return "\n".join([
        "<<ポジションクローズ>>",
        "[{0:}<={1:}]",
        "ASK: {2:,.0f}",
        "BID: {3:,.0f}",
        "VOL: {4:}",
        "確定利益: {5:,.0f}円",
        "取引ID: {6:}",
        "---",
        "ポジションクローズにより{5:,.0f}円の利益が確定しました。"
    ]).format(*param)

class Notificator:

    def __init__(self):

        self._formatter = defaultdict(lambda: lambda x: x)
        self._formatter['found_open'] = self._format_found_open
        self._formatter['open_pair'] = self._format_open
        self._formatter['found_close'] = self._format_found_close
        self._formatter['close_pair'] = self._format_close

    def _format_open(self, data):
        return _format_open(data)

    def _format_found_open(self, data):
        return _format_found_open(data)

    def _format_close(self, data):
        return _format_close(data)

    def _format_found_close(self, data):
        return _format_found_close(data)

    def post_message(self, trigger_name, data):

        func = self._formatter[trigger_name]
        message = func(data)
        self._post_message('\n'+message)

        return message

class LINENotificator(Notificator):

    def __init__(self, params):

        super().__init__()
        self.enable = params.enable
        self.token = params.token
        self.url = params.url

    def _post_message(self, message):

        headers = { 'Authorization': 'Bearer '+ self.token }
        params = { 'message': message }
        payload = {
            'headers': headers,
            'params': params,
            'files': None
        }

        return requests.post(self.url, **payload)

class SlackNotificator(Notificator):

    def __init__(self, params):
        super().__init__()

        self.enable = params.enable
        self.url = params.url

    def _post_message(self, message):

        payload = {
            "text": message,
            "icon_emoji": ":moneybag:",
        }

        requests.post(self.url, json.dumps(payload))


class MutimediaNotificator:

    classes = {
        'line': LINENotificator,
        'slack': SlackNotificator,
    }

    def __init__(self, notify_params):

        def instantie(acc, item):
            name, params = item
            if params.enable:
                acc[name] = self.classes[name](params)
            return acc
        self._notificators = reduce(instantie, notify_params.items(), {})

    def broadcast_message(self, trigger_name, data):

        return [ notificator.post_message(trigger_name, data)
            for _, notificator in self._notificators.items() ]
