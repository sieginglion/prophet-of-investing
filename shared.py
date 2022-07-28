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


def get_investments_and_betters(market, symbol_to_score):
    ranking_list = [
        symbol
        for symbol, _ in sorted(
            symbol_to_score.items(), key=lambda x: x[1], reverse=True
        )
    ]
    investments = [
        row[0]
        for row in gspread.service_account('service_account.json')
        .open('First Step')
        .get_worksheet(0)
        .get({'Crypto': config.crypto.range, 'Stock': config.stock.range}[market])
    ]
    investments = [symbol for symbol in ranking_list if symbol in investments]
    worst_i = ranking_list.index(investments[-1])
    betters = [symbol for symbol in ranking_list[:worst_i] if symbol not in investments]
    return investments, betters


def notify(text):
    r.post(
        f'https://api.telegram.org/bot{ config.bot_token }/sendMessage',
        json={'chat_id': 1075192674, 'text': text},
    ).json()
