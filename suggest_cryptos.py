import time
import traceback

import numpy as np

from shared import *

n_caps = config.crypto.box * 2


def get_cryptos():
    resp = r.get(
        f'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page={ config.crypto.top }'
    )
    return resp.json()


def get_caps(crypto):
    resp = r.get(
        f'https://api.coingecko.com/api/v3/coins/{ crypto["id"] }/market_chart?vs_currency=usd&days={ n_caps + 1 }&interval=daily'
    )
    return [cap[1] for cap in resp.json()['market_caps'][-n_caps:]]


def calc_momentum(caps):
    box = config.crypto.box
    caps = np.convolve(np.array(caps), np.full(box, 1 / box), 'valid')
    return caps[-1] - caps[0]


def get_symbol_to_momentum():
    symbol_to_momentum = {}
    for crypto in get_cryptos():
        caps = get_caps(crypto)
        if len(caps) == n_caps and all(caps):
            symbol = crypto['symbol'].upper()
            if 'USD' not in symbol:
                symbol_to_momentum[symbol] = calc_momentum(caps)
        time.sleep(1)
    return symbol_to_momentum


if __name__ == '__main__':
    try:
        symbol_to_momentum = get_symbol_to_momentum()
        invests, betters = get_invests_and_betters('Crypto', symbol_to_momentum)
        notify('\n'.join(invests + [''] + betters))
    except:
        notify(traceback.format_exc())
