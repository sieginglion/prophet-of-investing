import os
import pickle
from typing import Any

import gspread
import requests as r
import yaml


class DotDict(dict):
    def __setattr__(self, k: str, v: Any) -> None:
        return super().__setitem__(k, v)

    def __getattr__(self, k: str) -> Any:
        return super().__getitem__(k)

    def __init__(self, d: dict = {}):
        for k, v in d.items():
            self[k] = DotDict(v) if isinstance(v, dict) else v

    def to_dict(self) -> dict:
        return {
            k: v.to_dict() if isinstance(v, DotDict) else v for k, v in self.items()
        }


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
        for row in first_step.get({'Crypto': 'A7:A8', 'Stock': 'A23:A27'}[market])
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
