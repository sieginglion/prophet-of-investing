import os
import pickle

import gspread
import requests as r
import yaml


class DotDict(object):
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, DotDict(v) if isinstance(v, dict) else v)


config = DotDict(yaml.safe_load(open('config.yaml', 'r')))


def cached(func):
    name = func.__name__
    cache = (
        pickle.load(open(f'{ name }.pkl', 'rb'))
        if os.path.isfile(f'{ name }.pkl')
        else {}
    )

    def func_(*args):
        if args not in cache:
            cache[args] = func(*args)
            pickle.dump(cache, open(f'{ name }.pkl', 'wb'))
        return cache[args]

    return func_


def get_invests(market):
    first_step = (
        gspread.service_account('service_account.json')
        .open('First Step')
        .get_worksheet(0)
    )
    return [
        row[0]
        for row in first_step.get({'Crypto': 'A7:A7', 'Stock': 'A22:A26'}[market])
    ]


def get_invests_and_betters(market, symbol_to_score):
    ranking_list = [
        symbol
        for symbol, _ in sorted(
            symbol_to_score.items(), key=lambda x: x[1], reverse=True
        )
    ]
    invests = get_invests(market)
    invests = [symbol for symbol in ranking_list if symbol in invests]
    worst_i = ranking_list.index(invests[-1])
    betters = [
        symbol for symbol in ranking_list[: worst_i + 1] if symbol not in invests
    ]
    return invests, betters


def notify(text):
    r.post(
        f'https://api.telegram.org/bot{ config.bot_token }/sendMessage',
        json={'chat_id': 1075192674, 'text': text},
    ).json()
