import time
import traceback
from collections import Counter

import numpy as np

from shared import *

n_qtr = 5 + (config.stock.box - 1)


def get_symbol_to_name_and_industry():
    resp = r.post(
        f'https://scanner.tradingview.com/america/scan',
        json={
            'filter': [
                {
                    'left': 'exchange',
                    'operation': 'in_range',
                    'right': ['AMEX', 'NASDAQ', 'NYSE'],
                },
                {'left': 'market_cap_basic', 'operation': 'nempty'},
                {'left': 'type', 'operation': 'in_range', 'right': ['stock', 'dr']},
            ],
            'options': {'lang': 'en_US'},
            'columns': ['name', 'description', 'industry'],
            'sort': {'sortBy': 'market_cap_basic', 'sortOrder': 'desc'},
            'range': [0, config.stock.top],
        },
    )
    return {
        row['d'][0].replace('.', '-'): tuple(row['d'][1:])
        for row in resp.json()['data']
    }


@cached
def get_revs(symbol):
    time.sleep(0.22)
    resp = r.get(
        f'https://financialmodelingprep.com/api/v3/income-statement/{ symbol }?period=quarter&limit={ n_qtr + 1 }&apikey={ config.stock.fmp_key }'
    )
    incomes = (
        sorted(resp.json(), key=lambda x: x['date'])[-n_qtr:]
        if resp.status_code == 200
        else []
    )
    return np.array([income['grossProfit'] for income in incomes])


def get_symbol_to_revs(symbols):
    symbol_to_revs = {}
    for symbol in symbols:
        revs = get_revs(symbol)
        if len(revs) == n_qtr and all(revs > 0):
            symbol_to_revs[symbol] = revs
        else:
            print(symbol)
    return symbol_to_revs


def calc_symbol_to_momentum(symbol_to_revs):
    box = config.stock.box
    symbol_to_momentum = {}
    for symbol, revs in symbol_to_revs.items():
        revs = np.convolve(revs, np.full(box, 1 / box), 'valid')
        symbol_to_momentum[symbol] = revs[-1] - revs[-5]
    return symbol_to_momentum


if __name__ == '__main__':
    try:
        symbol_to_name_and_industry = get_symbol_to_name_and_industry()
        symbols = list(symbol_to_name_and_industry.keys())
        symbol_to_revs = get_symbol_to_revs(symbols)
        symbol_to_momentum = calc_symbol_to_momentum(symbol_to_revs)
        invests, betters = get_invests_and_betters('Stock', symbol_to_momentum)
        hot_industry = Counter(
            symbol_to_name_and_industry[symbol][1] for symbol in betters
        ).most_common(1)[0][0]
        message = invests + [hot_industry]
        for symbol in betters:
            name, industry = symbol_to_name_and_industry[symbol]
            if industry != hot_industry:
                message.append(f'{ symbol } { industry }')
        notify('\n'.join(message))
    except:
        notify(traceback.format_exc())
