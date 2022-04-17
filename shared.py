import os
import pickle

import gspread
import requests as r
import yaml


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

    def func_(*args):
        if args not in cache:
            cache[args] = func(*args)
            pickle.dump(cache, open(func.__name__, 'wb'))
        return cache[args]

    return func_


def Float(x):
    try:
        return float(x)
    except Exception:
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


def get_invests_and_betters(market, symbol_to_score):
    ranking_list = [
        symbol
        for symbol, _ in sorted(
            symbol_to_score.items(), key=lambda x: x[1], reverse=True
        )
    ]
    invests, ratio = get_invests_and_ratio(market)
    invests = [symbol for symbol in ranking_list if symbol in invests]
    worst_i = ranking_list.index(invests[-1])
    betters = [
        symbol for symbol in ranking_list[: worst_i + 1] if symbol not in invests
    ]
    # return invests, filter_overvalued(market, betters, ratio)
    return invests, betters


def notify(text):
    r.post(
        f'https://api.telegram.org/bot{ config.bot_token }/sendMessage',
        json={'chat_id': 1075192674, 'text': text},
    ).json()
