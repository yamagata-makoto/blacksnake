#!/user/bin/env python
import pickle


def load_deals():
    deals = []
    with open('deals.pcl', 'rb') as f:
        deals = pickle.load(f)
    return deals

def singleleg_sides(deal):
    current_status, data = deal
    sides = []
    if current_status in ['confirm_open', 'confirm_close']:
        orders = data['orders']
        for _, result in orders.items():
            if ('id' in result) and (result['status'] != 'closed'):
                sides.append(result['side'].lower())
    return sides

def main():
    deals = load_deals()
    for i, deal in enumerate(deals):
        sides = singleleg_sides(deal)
        state_name, data = deal
        args = {
            'n': i,
            'state_name': state_name,
            'sides': '/'.join(sides),
            'profit': data['expected_profit']
        }
        print("{n:2d}|{state_name:13s}|{sides:4s}|{profit:7.2f}".format(**args))

if __name__ == '__main__':
    main()
