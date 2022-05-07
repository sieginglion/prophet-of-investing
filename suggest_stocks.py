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
                {'left': 'market_cap_basic', 'operation': 'nempty'},
                {'left': 'type', 'operation': 'in_range', 'right': ['stock', 'dr']},
                {
                    'left': 'exchange',
                    'operation': 'in_range',
                    'right': ['AMEX', 'NASDAQ', 'NYSE'],
                },
            ],
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
def over_usd(currency):
    time.sleep(0.22)
    resp = r.get(
        f'https://financialmodelingprep.com/api/v3/quote/USD{ currency }?apikey={ config.stock.fmp_key }'
    )
    return resp.json()[0]['price']


@cached
def get_profits(symbol):
    time.sleep(0.22)
    resp = r.get(
        f'https://financialmodelingprep.com/api/v3/income-statement/{ symbol }?period=quarter&limit={ n_qtr + 1 }&apikey={ config.stock.fmp_key }'
    )
    incomes = (
        sorted(resp.json(), key=lambda x: x['date'])[-n_qtr:]
        if resp.status_code == 200
        else []
    )
    return np.array(
        [
            income['grossProfit'] / over_usd(income['reportedCurrency'])
            for income in incomes
        ]
    )


def get_symbol_to_profits(symbols):
    symbol_to_profits = {}
    for symbol in symbols:
        profits = get_profits(symbol)
        if len(profits) == n_qtr and all(profits > 0):
            symbol_to_profits[symbol] = profits
        else:
            print(symbol)
    return symbol_to_profits


def calc_symbol_to_momentum(symbol_to_profits):
    box = config.stock.box
    symbol_to_momentum = {}
    for symbol, profits in symbol_to_profits.items():
        profits = np.convolve(profits, np.full(box, 1 / box), 'valid')
        symbol_to_momentum[symbol] = profits[-1] - profits[0]
    return symbol_to_momentum


if __name__ == '__main__':
    try:
        symbol_to_name_and_industry = get_symbol_to_name_and_industry()
        symbols = list(symbol_to_name_and_industry.keys())
        symbol_to_profits = get_symbol_to_profits(symbols)
        symbol_to_momentum = calc_symbol_to_momentum(symbol_to_profits)
        invests, betters = get_invests_and_betters('Stock', symbol_to_momentum)
        hottest = Counter(
            symbol_to_name_and_industry[symbol][1] for symbol in betters
        ).most_common(1)[0][0]
        message = invests + [hottest]
        for symbol in betters:
            name, industry = symbol_to_name_and_industry[symbol]
            if industry != hottest:
                message.append(f'{ symbol } { industry }')
        notify('\n'.join(message))
    except:
        notify(traceback.format_exc())
