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
    time.sleep(1)
    resp = r.get(
        f'https://api.coingecko.com/api/v3/coins/{ crypto["id"] }/market_chart?vs_currency=usd&days={ n_caps + 1 }&interval=daily'
    )
    caps = sorted(resp.json()['market_caps'], key=lambda x: x[0])[-n_caps:]
    return np.array([cap[1] for cap in caps])


def get_symbol_to_caps():
    symbol_to_caps = {}
    for crypto in get_cryptos():
        symbol = crypto['symbol'].upper()
        if 'USD' not in symbol:
            caps = get_caps(crypto)
            if len(caps) == n_caps and all(caps > 0):
                symbol_to_caps[symbol] = caps
    return symbol_to_caps


def calc_symbol_to_momentum(symbol_to_caps):
    box = config.crypto.box
    symbol_to_momentum = {}
    for symbol, caps in symbol_to_caps.items():
        caps = np.convolve(np.array(caps), np.full(box, 1 / box), 'valid')
        symbol_to_momentum[symbol] = caps[-1] - caps[0]
    return symbol_to_momentum


if __name__ == '__main__':
    try:
        symbol_to_caps = get_symbol_to_caps()
        symbol_to_momentum = calc_symbol_to_momentum(symbol_to_caps)
        invests, betters = get_invests_and_betters('Crypto', symbol_to_momentum)
        notify('\n'.join(invests + [''] + betters))
    except:
        notify(traceback.format_exc())
