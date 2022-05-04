import traceback

import requests as r

from shared import *


def get_symbol_to_cap():
    resp = r.get(
        f'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page={ config.crypto.top }'
    )
    return {
        crypto['symbol'].upper(): crypto['market_cap']
        for crypto in resp.json()
        if 'usd' not in crypto['symbol']
    }


if __name__ == '__main__':
    try:
        symbol_to_cap = get_symbol_to_cap()
        invests, betters = get_invests_and_betters('Crypto', symbol_to_cap)
        notify('\n'.join(invests + [''] + betters))
    except:
        notify(traceback.format_exc())
