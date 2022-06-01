import re
import traceback

import arrow
import requests as r

from shared import *


def get_symbols():
    resp = r.get(
        f'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page={ config.crypto.top }'
    )
    return [crypto['symbol'].upper() for crypto in resp.json()]


def get_symbol_to_profit(symbols):
    resp = r.get('https://tokenterminal.com/terminal/metrics/protocol_revenue')
    ID = re.search('static/.{,30}/_buildManifest\.js', resp.text).group(0)[7:-18]
    resp = r.get(
        f'https://tokenterminal.com/_next/data/{ ID }/terminal/metrics/protocol_revenue.json'
    )
    data = resp.json()['pageProps']
    project_to_symbol = {
        project['name']: project['symbol'] for project in data['projectsV2']
    }
    then = (
        arrow.now('UTC')
        .shift(days=-(config.crypto.window + 1))
        .format('YYYY-MM-DDTHH:mm:ssZZ')
    )
    symbol_to_profit = dict.fromkeys(symbols, 0)
    for daily in data['protocolRevenueData']['daily']:
        if (project := daily['project']) in project_to_symbol:
            if (symbol := project_to_symbol[project]) in symbol_to_profit:
                if daily['datetime'] < then and daily['revenue_protocol']:
                    symbol_to_profit[symbol] += daily['revenue_protocol']
    return symbol_to_profit


if __name__ == '__main__':
    try:
        symbols = get_symbols()
        symbol_to_profit = get_symbol_to_profit(symbols)
        invests, betters = get_invests_and_betters('Crypto', symbol_to_profit)
        notify('\n'.join(invests + [''] + betters))
    except:
        notify(traceback.format_exc())
