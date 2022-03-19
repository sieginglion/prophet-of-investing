import os
import yaml
import pickle
import gspread
import requests as r


class DotDict(object):
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, DotDict(v) if isinstance(v, dict) else v)


with open('config.yaml', 'r') as f:
    config = DotDict(yaml.safe_load(f))


def cached(func):
    if os.path.isfile(func.__name__):
        cache = pickle.load(open(func.__name__, 'rb'))
    else:
        cache = {}

    def func_(*param):
        if param not in cache:
            cache[param] = func(*param)
            pickle.dump(cache, open(func.__name__, 'wb'))
        return cache[param]

    return func_


def Float(x):
    try:
        return float(x)
    except:
        return 0


def get_invests_and_ratio(market):
    first_step = (
        gspread.service_account('service_account.json')
        .open('First Step')
        .get_worksheet(0)
    )
    invests = [
        row[0]
        for row in first_step.get({'Crypto': 'A11:A20', 'Stock': 'A35:A39'}[market])
    ]
    ratio = first_step.get('K6', value_render_option='UNFORMATTED_VALUE')[0][0]
    return invests, ratio


def filter_overvalued(market, symbols, ratio):
    undervalued = []
    for symbol in symbols:
        resp = r.get(
            f'https://us-central1-generated-armor-274023.cloudfunctions.net/CalcTargetPrice?market={ market }&symbol={ symbol }&ratio={ ratio }'
        )
        if resp.status_code == 200 and resp.json()['undervalued']:
            undervalued.append(symbol)
    return undervalued


def find_worst_and_better(market, symbol_to_score):
    invests, ratio = get_invests_and_ratio(market)
    ranking_list = [
        symbol
        for symbol, _ in sorted(
            symbol_to_score.items(), key=lambda x: x[1], reverse=True
        )
    ]
    worst_i = max(ranking_list.index(invest) for invest in invests)
    better = [symbol for symbol in ranking_list[: worst_i + 1] if symbol not in invests]
    return ranking_list[worst_i], filter_overvalued(market, better, ratio)


def notify(text):
    r.post(
        f'https://api.telegram.org/bot{ config.bot_token }/sendMessage',
        json={'chat_id': 1075192674, 'text': text},
    ).json()
