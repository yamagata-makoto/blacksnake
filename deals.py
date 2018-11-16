import pickle


def load_deals():
    deals = []
    with open('deals.pcl', 'rb') as f:
        deals = pickle.load(f)
    return deals

def singleopen_sides(deal):
    current_status, data = deal
    sides = []
    if current_status == 'confirm_open':
        orders = data['orders']
        for _, result in orders.items():
            if ('id' in result) and (result['status'] != 'closed'):
                sides.append(result['side'].lower())
    return sides

def main():
    deals = load_deals()
    for i, deal in enumerate(deals):
        sides = singleopen_sides(deal)
        print("{0:d}:{1:s}:{2:s}".format(i, deal[0], '/'.join(sides)))

if __name__ == '__main__':
    main()
