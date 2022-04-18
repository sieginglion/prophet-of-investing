import time
import traceback
from collections import Counter

import numpy as np

from shared import *

n_qtr = 5 + (config.stock.box - 1)


def get_symbol_to_name_and_industry(top):
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
            'range': [0, top],
        },
    )
    return {
        row['d'][0].replace('.', '-'): tuple(row['d'][1:])
        for row in resp.json()['data']
    }


@cached
def get_revs(symbol):
    alpha_keys = config.stock.alpha_keys
    time.sleep(12 / len(alpha_keys) * 1.1)
    resp = r.get(
        f'https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={ symbol }&apikey={ alpha_keys[0] }'
    )
    alpha_keys.append(alpha_keys.pop(0))
    incomes = sorted(
        resp.json().get('quarterlyReports', []), key=lambda x: x['fiscalDateEnding']
    )[-n_qtr:]
    return np.array([Float(income['grossProfit']) for income in incomes])


def calc_rev(revs):
    box = config.stock.box
    return sum(revs[-box:]) / box


def calc_growth(revs):
    box = config.stock.box
    revs = np.convolve(revs, np.full(box, 1 / box), 'valid')
    return revs[-1] / revs[0]


def calc_symbol_to_score(symbol_to_revs):
    symbol_to_rev_and_growth = {}
    for symbol, revs in symbol_to_revs.items():
        if len(revs) == n_qtr and all(revs > 0):
            symbol_to_rev_and_growth[symbol] = (calc_rev(revs), calc_growth(revs))
    revs, growths = [], []
    for rev, growth in symbol_to_rev_and_growth.values():
        revs.append(rev)
        growths.append(growth)
    revs, growths = np.array(revs), np.array(growths)
    return {
        symbol: np.sum(revs <= rev) * np.sum(growths <= growth)
        for symbol, (rev, growth) in symbol_to_rev_and_growth.items()
    }


if __name__ == '__main__':
    try:
        symbol_to_name_and_industry = get_symbol_to_name_and_industry(config.stock.top)
        symbols = list(symbol_to_name_and_industry.keys())
        symbol_to_revs = {symbol: get_revs(symbol) for symbol in symbols}
        symbol_to_score = calc_symbol_to_score(symbol_to_revs)
        invests, betters = get_invests_and_betters('Stock', symbol_to_score)
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
