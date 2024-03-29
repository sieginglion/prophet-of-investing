import time
from collections import Counter

import numpy as np

from shared import *


N_QTR = 5 + (config.stock.window - 1)


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
def get_usd_over_x(currency):
    resp = r.get(
        f'https://financialmodelingprep.com/api/v3/quote/USD{ currency }?apikey={ config.stock.fmp_key }'
    )
    time.sleep(0.22)
    return resp.json()[0]['price']


@cached
def get_profits(symbol):
    resp = r.get(
        f'https://financialmodelingprep.com/api/v3/income-statement/{ symbol }?period=quarter&limit={ N_QTR + 1 }&apikey={ config.stock.fmp_key }'
    )
    time.sleep(0.22)
    incomes = (
        sorted(resp.json(), key=lambda x: x['date']) if resp.status_code == 200 else []
    )
    return np.array(
        [
            income['grossProfit'] / get_usd_over_x(income['reportedCurrency'])
            for income in incomes
        ]
    )


def get_symbol_to_profits(symbols):
    symbol_to_profits = {}
    for symbol in symbols:
        profits = get_profits(symbol)[-N_QTR:]
        if len(profits) == N_QTR and all(profits > 0):
            symbol_to_profits[symbol] = profits
        else:
            print(symbol)
    return symbol_to_profits


def calc_symbol_to_momentum(symbol_to_profits):
    window = config.stock.window
    symbol_to_momentum = {}
    for symbol, profits in symbol_to_profits.items():
        profits = np.convolve(profits, np.full(window, 1 / window), 'valid')
        symbol_to_momentum[symbol] = profits[-1] - profits[0]
    return symbol_to_momentum


def gen_message(investments, suggestions):
    message = investments
    hot, _ = zip(
        *Counter(
            symbol_to_name_and_industry[symbol][1] for symbol in suggestions
        ).most_common(2)
    )
    message.extend(hot)
    for symbol in suggestions:
        name, industry = symbol_to_name_and_industry[symbol]
        if industry not in hot:
            message.append(f'{ symbol }  { name }  { industry }')
    return '\n'.join(message)


if __name__ == '__main__':
    symbol_to_name_and_industry = get_symbol_to_name_and_industry()
    symbols = list(symbol_to_name_and_industry.keys())
    symbol_to_profits = get_symbol_to_profits(symbols)
    symbol_to_momentum = calc_symbol_to_momentum(symbol_to_profits)
    investments, suggestions = get_investments_and_suggestions(
        'Stock', symbol_to_momentum
    )
    message(gen_message(investments, suggestions))
