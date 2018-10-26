from functools import partial
import datetime

OPENING_MESSAGE = """
Blacksname Bitcoin Arbitrage
DISCLAIMER: USE THE SOFTWARE AT YOUR OWN RISK

-------------------------------------------------
| Blacksnake Bitcoin Arbitrage System           |
-------------------------------------------------
"""
STARTED_ON = "Blacksnake started on {}\n"
ARBITRAGE_FORM = """[ Arbitrage Status: {} ]
    Best ask         : {:10s} Ask {:,.0f} {:5.3f} 
    Best bid         : {:10s} Bid {:,.0f} {:5.3f}
    Spread           : {:,.0f}
    Available volume : {:5.3f}
    Target volume    : {:5.3f}
    Expected profit  : {:,.0f} ({:5.3f}%)
"""
POSITION_FORM = ", ".join([
    "    {:10s}  : {:5.3f} BTC",
    "LongEntry: {:s}",
    "ShortEntry: {:s}",
])

PAIRS_FORM = " ".join([
    "    >>{0:10s}",
    "{1:,.0f}",
    "{2:5.3f}",
    "=>",
    "{3:10s}",
    "{4:,.0f}",
    "{5:5.3f}",
    "|",
    "{6:,.0f}",
    "|",
    "{7:,.0f}",
])

_ = lambda s: s[0].upper() + s[1:]

class CUI:

    def __init__(self, date):

        print(OPENING_MESSAGE)
        print(STARTED_ON.format(date))


    def show_arbitrage(self, plan):

        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ask = plan.best('ask')
        bid = plan.best('bid')
        profit, percent = plan.expected_profit()
        print(ARBITRAGE_FORM.format(
            now,
            _(ask['exchange_name']),
            ask['quote'][0],
            ask['quote'][1],
            _(bid['exchange_name']),
            bid['quote'][0],
            bid['quote'][1],
            plan.spread(),
            plan.available_volume(),
            plan.target_volume(),
            profit,
            percent))

    def show_positions(self, plan):

        positions = plan.positions()
        net_exposure = positions.net_exposure()
        is_ok = lambda b: '[{}]'.format('OK' if b else 'NG')
        print("[ Net Exposure {:5.3f} BTC ]".format(net_exposure))
        for name, value in positions.items():
            balance, status = value 
            print(POSITION_FORM.format(
                _(name),
                balance['BTC']['free'],
                is_ok(status[0]),
                is_ok(status[1]),
            ))
        print("")

    def show(self, s):
        print(s)

    def show_openpairs(self, data):

        sell = data['sell']
        buy  = data['buy']
        print(PAIRS_FORM.format(
            buy['exchange_name'],
            buy['quote'][0],
            buy['quote'][1],
            sell['exchange_name'],
            sell['quote'][0],
            sell['quote'][1],
            data['open_deal']['expected_profit'],
            -data['expected_profit'],
            ))
        print("")

_cui = CUI(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

def show_arbitrage(plan):
    return _cui.show_arbitrage(plan)

def show_positions(plan):
    return _cui.show_positions(plan)

def show_openpairs(data):
    return _cui.show_openpairs(data)
