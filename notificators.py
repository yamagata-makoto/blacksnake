import requests


class LINENotificator:

    def __init__(self, params):

        self.enable = params.enable
        self.token = params.token
        self.url = params.url
        self._formatter = {
            'found_open': self._format_found_open,
            'open_pair': self._format_open,
            'found_close': self._format_found_close,
            'close_pair': self._format_close,
        }

    def post_message(self, trigger_name, data):

        func = self._formatter[trigger_name]
        message = func(data)
        self._post_message(message)

    def _format_open(self, data):

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
            data['deal_id'],
        ) 
        return "\n".join([
            "[{0:}=>{1:}]",
            "ASK: {2:,.0f}",
            "BID: {3:,.0f}",
            "VOL: {4:}",
            "取引ID:{7:}が約定しました。",
            "{5:,.0f}円を投下し{6:,.0f}円の暫定利益を確保しました。",
        ]).format(*param)

    def _format_found_open(self, data):

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
            data['deal_id'],
        ) 
        return "\n".join([
            "[{0:}=>{1:}]",
            "ASK: {2:,.0f}",
            "BID: {3:,.0f}",
            "VOL: {4:}",
            "{5:,.0f}円を投下し{6:,.0f}円の暫定利益を得られる取引を発見しました。",
            "取引ID:{7:}",
            "注文を送信します。"
        ]).format(*param)

    def _format_found_close(self, data):
        sell = data['sell']
        buy  = data['buy']
        profit = data['open_deal']['expected_profit'] - data['expected_profit']
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
            "[{0:}<={1:}]",
            "ASK: {2:,.0f}",
            "BID: {3:,.0f}",
            "VOL: {4:}",
            "取引ID:{7:}をクローズします。",
            "{5:,.0f}円の利確コストを使い{6:,.0f}円の利益を確定させる取引を発見しました。",
            "注文を送信します。"
        ]).format(*param)

    def _format_close(self, data):
        sell = data['sell']
        buy  = data['buy']
        profit = data['open_deal']['expected_profit'] - data['expected_profit']
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
            "[{0:}<={1:}]",
            "ASK: {2:,.0f}",
            "BID: {3:,.0f}",
            "VOL: {4:}",
            "取引ID:{7:}が約定しました。",
            "{5:,.0f}円の利確コストを使い{6:,.0f}円の利益を確定させました。",
        ]).format(*param)

    def _post_message(self, message):

        headers = { 'Authorization': 'Bearer '+ self.token }
        params = { 'message': message }
        payload = {
            'headers': headers,
            'params': params,
            'files': None
        }
        return requests.post(self.url, **payload)

