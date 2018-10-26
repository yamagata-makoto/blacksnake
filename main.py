import time
import config
import cui
from arbtools import Provider
from notificators import LINENotificator


def planned(sender, plan):

    cui.show_arbitrage(plan)
    cui.show_positions(plan)

def found_open(sender, data, notify):

    notify.post_message('found_open', data)

def open_pair(sender, data, notify):

    notify.post_message('open_pair', data)

def found_close(sender, data, notify):

    notify.post_message('found_close', data)

def close_pair(sender, data, notify):

    notify.post_message('close_pair', data)

def lookup_close(sender, data, notify):

    cui.show_openpairs(data)

if __name__ == '__main__':

    cfg = config.load()

    provider = Provider(cfg.exchanges)
    broker = provider.broker(cfg.trade).load_from('deals.pcl')
    notify = LINENotificator(cfg.notify.line)

    broker.on('planned', planned)
    broker.on('found_open', found_open, notify=notify)
    broker.on('open_pair', open_pair, notify=notify)
    broker.on('found_close', found_close, notify=notify)
    broker.on('close_pair', close_pair, notify=notify)
    broker.on('lookup_close', lookup_close, notify=notify)

    while True:

        quotes = provider.orderbooks().round().quotes()
        plan = broker.planning(quotes)
        broker.request(plan.deal()).save_to('deals.pcl')
        broker.process_requests()
        time.sleep(3)

