from collections import defaultdict
import requests


class LINENotificator:

    def __init__(self, params):

        self.enable = params.enable
        self.token = params.token
        self.url = params.url
        self._formatter = defaultdict(lambda: lambda x: x)
        self._formatter['found_open'] = self._format_found_open
        self._formatter['open_pair'] = self._format_open
        self._formatter['found_close'] = self._format_found_close
        self._formatter['close_pair'] = self._format_close

    def post_message(self, trigger_name, data):

        func = self._formatter[trigger_name]
        message = func(data)
        self._post_message(message)
        
        return message

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
            data['expected_profit']/2.0,
            data['deal_id'],
        ) 
        return "\n".join([
            "",
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
            data['expected_profit']/2.0,
            data['deal_id'],
        ) 
        return "\n".join([
            "",
            "<<裁定機会検出>>",
            "[{0:}=>{1:}]",
            "ASK: {2:,.0f}",
            "BID: {3:,.0f}",
            "VOL: {4:}",
            "投下資本: {5:,.0f}円",
            "暫定利益: {6:,.0f}円",
            "想定利益: {7:,.0f}円",
            "取引ID:{8:}",
            "注文を送信します。"
        ]).format(*param)

    def _format_found_close(self, data):
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
            "",
            "<<利確機会検出>>",
            "[{0:}<={1:}]",
            "ASK: {2:,.0f}",
            "BID: {3:,.0f}",
            "VOL: {4:}",
            "利確コスト: {5:,.0f}円",
            "想定利益: {6:,.0f}円",  
            "取引ID: {7:}",
            "注文を送信します。"
        ]).format(*param)

    def _format_close(self, data):
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
            "",
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

    def _post_message(self, message):

        headers = { 'Authorization': 'Bearer '+ self.token }
        params = { 'message': message }
        payload = {
            'headers': headers,
            'params': params,
            'files': None
        }
        return requests.post(self.url, **payload)

