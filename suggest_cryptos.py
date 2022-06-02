import re
import traceback
from collections import defaultdict

import arrow
import requests as r

from shared import *


def get_symbol_to_cap():
    resp = r.get(
        f'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page={ config.crypto.top }'
    )
    return {crypto['symbol'].upper(): crypto['market_cap'] for crypto in resp.json()}


def get_symbol_to_gross():
    resp = r.get('https://tokenterminal.com/terminal/metrics/protocol_revenue')
    ID = re.search('static/.{,30}/_buildManifest\.js', resp.text).group(0)[7:-18]
    resp = r.get(
        f'https://tokenterminal.com/_next/data/{ ID }/terminal/metrics/revenue.json'
    )
    project_to_symbol = {
        project['name']: project['symbol']
        for project in resp.json()['pageProps']['projectsV2']
    }
    resp = r.get(
        f'https://tokenterminal.com/_next/data/{ ID }/terminal/metrics/protocol_revenue.json'
    )
    then = (
        arrow.utcnow()
        .shift(days=-(config.crypto.window + 1))
        .format('YYYY-MM-DDTHH:mm:ssZZ')
    )
    symbol_to_gross = defaultdict(float)
    for daily in resp.json()['pageProps']['protocolRevenueData']['daily']:
        if daily['datetime'] > then:
            if (project := daily['project']) in project_to_symbol:
                if gross := daily['revenue_protocol']:
                    symbol_to_gross[project_to_symbol[project]] += gross
    return symbol_to_gross


def calc_symbol_to_pg(symbol_to_cap, symbol_to_gross):
    symbol_to_pg = {}
    for symbol, cap in symbol_to_cap.items():
        if gross := symbol_to_gross.get(symbol):
            symbol_to_pg[symbol] = cap / gross
    return symbol_to_pg


if __name__ == '__main__':
    try:
        symbol_to_cap = get_symbol_to_cap()
        symbol_to_gross = get_symbol_to_gross()
        symbol_to_pg = calc_symbol_to_pg(symbol_to_cap, symbol_to_gross)
        invests, betters = get_invests_and_betters(
            'Crypto', {symbol: -pg for symbol, pg in symbol_to_pg.items()}
        )
        notify('\n'.join(invests + [''] + betters))
    except:
        notify(traceback.format_exc())
