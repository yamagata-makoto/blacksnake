import traceback
import time
import config
import cui
from arbtools import Provider
from notificators import LINENotificator


def planned(sender, plan):

    cui.show_arbitrage(plan)
    cui.show_positions(plan)

def reverse_planned(sender, data):

    cui.show_openpairs(data)

def quote_error(sender, errors):
    pass
        
def balance_error(sender, errors):
    for k, v in errors.items():
        print(k, v)

def found_open(sender, data, notify):

    notify.post_message('found_open', data)

def open_pair(sender, data, notify):

    notify.post_message('open_pair', data)

def found_close(sender, data, notify):

    notify.post_message('found_close', data)

def close_pair(sender, data, notify):

    notify.post_message('close_pair', data)


def trade_loop(interval):

    while True:
        quotes = provider.orderbooks().round().quotes()
        plan = broker.planning(quotes)
        broker.request(plan.deal())
        broker.process_requests().save_to('deals.pcl')
        time.sleep(cfg.system.interval)

if __name__ == '__main__':

    cfg = config.load()
    notify = LINENotificator(cfg.notify.line)
    try:
        provider = Provider(cfg.exchanges)
        broker = provider.broker(cfg.trade).load_from('deals.pcl')

        broker.on('planned', planned)
        broker.on('reverse_planned', reverse_planned)
        broker.on('quote_error', quote_error)
        broker.on('balance_error', balance_error)
        broker.on('found_open', found_open, notify=notify)
        broker.on('open_pair', open_pair, notify=notify)
        broker.on('found_close', found_close, notify=notify)
        broker.on('close_pair', close_pair, notify=notify)

        trade_loop(cfg.system.interval)

    except Exception as e:
        msg = notify.post_message(None, traceback.format_exc()) 
        print(msg)

