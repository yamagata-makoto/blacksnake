import traceback
import time
import datetime
import schedule
import config
import cui
from arbtools import Provider
from notificators import MutimediaNotificator


DATA_ = {}

def scheduled_task(notify):

    plan = DATA_['plan']
    msg = cui.show_positions(plan, printfunc=lambda x: x)
    notify.broadcast_message(None, msg)

def planned(sender, plan):

    cui.show_arbitrage(plan)
    cui.show_positions(plan)
    DATA_['plan'] = plan

def reverse_planned(sender, data):

    cui.show_openpairs(data)

def quote_error(sender, errors, notify):

    for k, v in errors.items():
        print(k, v)

def balance_error(sender, errors, notify):

    for k, v in errors.items():
        print(k, v)

def found_open(sender, data, notify):

    notify.broadcast_message('found_open', data)

def open_pair(sender, data, notify):

    notify.broadcast_message('open_pair', data)

def found_close(sender, data, notify):

    notify.broadcast_message('found_close', data)

def close_pair(sender, data, notify):

    notify.broadcast_message('close_pair', data)

def trade_loop(interval):

    while True:

        schedule.run_pending()

        quotes = provider.orderbooks().round().quotes()
        plan = broker.planning(quotes)

        broker.request(plan.deal())
        broker.process_requests().save_to('deals.pcl')

        time.sleep(interval)

if __name__ == '__main__':

    cfg = config.load()
    notify = MutimediaNotificator(cfg.notify)
    try:
        provider = Provider(cfg.exchanges)
        broker = provider.broker(cfg.trade).load_from('deals.pcl')

        broker.on('planned', planned)
        broker.on('reverse_planned', reverse_planned)
        broker.on('quote_error', quote_error, notify=notify)
        broker.on('balance_error', balance_error, notify=notify)
        broker.on('found_open', found_open, notify=notify)
        broker.on('open_pair', open_pair, notify=notify)
        broker.on('found_close', found_close, notify=notify)
        broker.on('close_pair', close_pair, notify=notify)

        schedule.every().day.at('07:00').do(scheduled_task, notify=notify)

        trade_loop(cfg.system.interval)

    except Exception as e:
        msg = traceback.format_exc()
        notify.broadcat_message(None, msg)
        print(msg)

