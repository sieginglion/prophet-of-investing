import time
import numpy as np
import traceback
from shared import *

n_qtr = 5 + (config.stock.box - 1)

def get_symbol_to_name_and_industry(country, top):
    filter = [] if country != 'america' else [{
        'left': 'exchange',
        'operation': 'in_range',
        'right': ['AMEX', 'NASDAQ', 'NYSE']
    }]
    resp = r.post(f'https://scanner.tradingview.com/{ country }/scan', json={
        'filter': filter + [
            {
                'left': 'market_cap_basic',
                'operation': 'nempty'
            },
            {
                'left': 'type',
                'operation': 'in_range',
                'right': ['stock', 'dr']
            }
        ],
        'options': {
            'lang': 'zh_TW' if country == 'taiwan' else 'en_US'
        },
        'columns': ['name', 'description', 'industry'],
        'sort': {
            'sortBy': 'market_cap_basic',
            'sortOrder': 'desc'
        },
        'range': [0, top]
    })
    return {row['d'][0].replace('.', '-'): tuple(row['d'][1:]) for row in resp.json()['data']}

@cached
def get_revs(symbol):
    time.sleep(0.25)
    resp = r.get(f'https://financialmodelingprep.com/api/v3/income-statement/{ symbol }?period=quarter&limit={ n_qtr }&apikey={ config.stock.fmp_key }')
    revs = np.array([income['grossProfit'] for income in sorted(resp.json(), key=lambda x: x['date'])]) if resp.status_code == 200 else []
    if not (len(revs) == n_qtr and all(revs > 0)):
        alpha_keys = config.stock.alpha_keys
        key = alpha_keys.pop(0); alpha_keys.append(key)
        resp = r.get(f'https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={ symbol }&apikey={ key }')
        incomes = sorted(resp.json().get('quarterlyReports', []), key=lambda x: x['fiscalDateEnding'])[-n_qtr:]
        revs = np.array([Float(income['grossProfit']) for income in incomes])
    return revs

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
        revs.append(rev); growths.append(growth)
    revs, growths = np.array(revs), np.array(growths)
    return {symbol: np.sum(revs <= rev) * np.sum(growths <= growth) for symbol, (rev, growth) in symbol_to_rev_and_growth.items()}

if __name__ == '__main__':
    try:
        symbol_to_name_and_industry = get_symbol_to_name_and_industry('america', config.stock.top)
        symbols = list(symbol_to_name_and_industry.keys())
        symbol_to_revs = {symbol: get_revs(symbol) for symbol in symbols}
        symbol_to_score = calc_symbol_to_score(symbol_to_revs)
        
        worst, better = find_worst_and_better('Stock', symbol_to_score)

        message = [worst]
        for symbol in better:
            name, industry = symbol_to_name_and_industry[symbol]
            message.append(f'{ symbol } { industry }')
        notify('\n'.join(message))
    except:
        err = traceback.format_exc()
        print(err); notify(err)
