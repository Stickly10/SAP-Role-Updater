"""Fixed-width table constants and regexes used by the core processor."""

from __future__ import annotations

import re

PREFIX_WIDTHS = {
    "table": 10,
    "sp40": 40,
    "mandt": 3,
    "role": 30,
    "counter": 6,
}

W1251 = {
    "object": 10,
    "auth": 12,
    "variant_pad": 4,
    "field": 10,
    "low": 40,
    "high": 40,
    "modified": 1,
    "deleted": 1,
    "copied": 1,
    "neu": 1,
    "node": 6,
}

W1252 = {
    "varbl": 10,
    "sp30": 30,
    "low": 40,
    "high": 40,
}

RX_1251 = re.compile(
    rf"^(?P<table>.{{{PREFIX_WIDTHS['table']}}})(?P<sp40>\s{{{PREFIX_WIDTHS['sp40']}}})"
    rf"(?P<mandt>\d{{{PREFIX_WIDTHS['mandt']}}})(?P<role>.{{{PREFIX_WIDTHS['role']}}})"
    rf"(?P<counter>\d{{{PREFIX_WIDTHS['counter']}}})(?P<object>.{{{W1251['object']}}})(?P<auth>.{{{W1251['auth']}}})"
    rf"(?P<variant_pad>.{{{W1251['variant_pad']}}})(?P<field>.{{{W1251['field']}}})(?P<low>.{{{W1251['low']}}})"
    rf"(?P<high>.{{{W1251['high']}}})(?P<modified>.{{{W1251['modified']}}})(?P<deleted>.{{{W1251['deleted']}}})"
    rf"(?P<copied>.{{{W1251['copied']}}})(?P<neu>.{{{W1251['neu']}}})(?P<node>.{{{W1251['node']}}})(?P<tail>.*)$"
)

RX_1252 = re.compile(
    rf"^(?P<table>.{{{PREFIX_WIDTHS['table']}}})(?P<sp40>\s{{{PREFIX_WIDTHS['sp40']}}})"
    rf"(?P<mandt>\d{{{PREFIX_WIDTHS['mandt']}}})(?P<role>.{{{PREFIX_WIDTHS['role']}}})"
    rf"(?P<counter>\d{{{PREFIX_WIDTHS['counter']}}})(?P<varbl>.{{{W1252['varbl']}}})(?P<sp30>\s{{{W1252['sp30']}}})"
    rf"(?P<low>.{{0,{W1252['low']}}})(?P<high>.{{0,{W1252['high']}}})(?P<tail>.*)$"
)

RX_1252_LEGACY = re.compile(
    rf"^(?P<table>.{{{PREFIX_WIDTHS['table']}}})(?P<sp40>\s{{{PREFIX_WIDTHS['sp40']}}})"
    rf"(?P<mandt>\d{{{PREFIX_WIDTHS['mandt']}}})(?P<role>.{{{PREFIX_WIDTHS['role']}}})"
    rf"(?P<counter>\d{{{PREFIX_WIDTHS['counter']}}})(?P<varbl>.{{{W1252['varbl']}}})(?P<sp30>\s{{{W1252['sp30']}}})"
    rf"(?P<low>.{{0,4}})(?P<tail>.*)$"
)
