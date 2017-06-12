#!/usr/bin/env python
# coding: utf-8

import io
import os
import glob
from datetime import datetime
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

import pytest

here = os.path.abspath(os.path.dirname(__file__))


# Menus where the menu was posted in a different week:
weeknum_override = {
    '161216-third.txt': 51,
    '161007-first.txt': 41,
    '160704-third.txt': 26,
    '160226-first.txt': 9,
    '160219-third.txt': 8,
    '160122-first.txt': 4,
    '160122-third.txt': 4,
    '160108-first.txt': 2,
    '160108-third.txt': 2,
}

# Days that are known to be missing from menus:
known_missing = {
    '161003-third.txt': (0,),
    '161108-third.txt': (0,),
    '161115-third.txt': (0,),
    '161122-third.txt': (0,),
    '160329-first.txt': (0,),
    '160329-third.txt': (0,),
    '170607-combined.txt': (0, 1),
}


@lru_cache(256)
def get_file(path):
    with io.open(path, encoding="utf8") as f:
        return f.read()


def _historical():
    dirname = os.path.join(here, 'historical')
    filenames = glob.glob(os.path.join(dirname, "*.txt"))
    return (fn for fn in filenames)


def _first_floor():
    for fn in _historical():
        if fn.endswith('-first.txt'):
            yield fn


def _third_floor():
    for fn in _historical():
        if fn.endswith('-third.txt'):
            yield fn

def _combined():
    for fn in _historical():
        if fn.endswith('-combined.txt'):
            yield fn


@lru_cache(256)
def _extract_week_num(path):
    filename = os.path.basename(path)
    if filename in weeknum_override:
        return weeknum_override[filename]
    filename = os.path.splitext(filename)[0]
    d = datetime.strptime(filename.split('-')[0], '%y%m%d')
    return d.isocalendar()[1]


@pytest.fixture(params=_historical())
def historical(request):
    path = request.param
    filename = os.path.basename(path)
    missing = known_missing.get(filename)
    return get_file(path), missing


@pytest.fixture(params=_first_floor())
def historical_first_floor(request):
    path = request.param
    week_num = _extract_week_num(path)
    return week_num, get_file(path)


@pytest.fixture(params=_third_floor())
def historical_third_floor(request):
    path = request.param
    week_num = _extract_week_num(path)
    return week_num, get_file(path)


@pytest.fixture(params=_combined())
def historical_combined(request):
    path = request.param
    week_num = _extract_week_num(path)
    return week_num, get_file(path)
