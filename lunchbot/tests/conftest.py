#!/usr/bin/env python
# coding: utf-8

import io
import os
import glob
from datetime import datetime, date
from collections import defaultdict
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

from pytz import timezone
import pytest

here = os.path.abspath(os.path.dirname(__file__))


# Menus where the menu was posted in a different week:
weeknum_override = {
    '161216-third.txt': (2016, 51),
    '161007-first.txt': (2016, 41),
    '160704-third.txt': (2016, 26),
    '160226-first.txt': (2016, 9),
    '160219-third.txt': (2016, 8),
    '160122-first.txt': (2016, 4),
    '160122-third.txt': (2016, 4),
    '160108-first.txt': (2016, 2),
    '160108-third.txt': (2016, 2),
    '180622-combined.txt': (2018, 26),
    '190104-combined.txt': (2019, 2),
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
    '170821-combined.txt': tuple(range(5)),
    '180103-combined.txt': (0, 1),
    # List of tuples: missing days, [(first floor), (third floor)]
    '180122-combined.txt': [(), (0,)],
    '180212-combined.txt': [(), (0,)],
    '180403-combined.txt': [(0,), (0, 1)],
    '180514-combined.txt': [(3, 4), ()],
    '180522-combined.txt': [(0,), (0, 1)],
    '180604-combined.txt': [(0, 1), ()],
    '180611-combined.txt': [(), (0, 1)],
    '180622-combined.txt': (0, 1, 2, 3),
    '180813-combined.txt': (0, 1, 2),
    '180827-combined.txt': (0,),
    '181210-combined.txt': (0,),
    '181217-combined.txt': (0, 1, 2, 3),
    '190102-combined.txt': (0, 1),
    '190211-combined.txt': (0, 1),
    '190218-combined.txt': (0,),
}

date_override = {
    '180503-dailycomb.txt': (2018, 5, 4),
}


@lru_cache(256)
def get_file(path):
    with io.open(path, encoding="utf8") as f:
        return f.read()


def _historical():
    dirname = os.path.join(here, 'historical')
    filenames = glob.glob(os.path.join(dirname, "*.txt"))
    return (fn for fn in filenames)

HISTORICAL = tuple(sorted(_historical()))


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

def _historical_weekly():
    for fn in _historical():
        if not fn.endswith('-dailycomb.txt'):
            yield fn

def _daily_combined():
    for fn in _historical():
        if fn.endswith('-dailycomb.txt'):
            yield fn

def _weeks():
    lut = defaultdict(list)
    for fn in _historical():
        if fn.endswith('-dailycomb.txt'):
            continue
        year_week = _extract_year_weeknum(fn)
        lut[year_week].append(fn)
        assert len(lut[year_week]) <= 2
    return lut




@lru_cache(256)
def _extract_year_weeknum(path):
    filename = os.path.basename(path)
    if filename in weeknum_override:
        return weeknum_override[filename]
    filename = os.path.splitext(filename)[0]
    d = datetime.strptime(filename.split('-')[0], '%y%m%d')
    return d.isocalendar()[:2]


def _extract_week_num(path):
    return _extract_year_weeknum(path)[1]

def _extract_date(path):
    filename = os.path.basename(path)
    if filename in date_override:
        return datetime(*date_override[filename], tzinfo=timezone('Europe/Oslo'))
    filename = os.path.splitext(filename)[0]
    d = datetime.strptime(filename.split('-')[0], '%y%m%d')
    return d.replace(tzinfo=timezone('Europe/Oslo'))


WEEKS = _weeks()

@pytest.fixture(params=_historical_weekly())
def historical_weekly(request):
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


@pytest.fixture(params=_daily_combined())
def historical_daily_post(request):
    path = request.param
    d = _extract_date(path)
    return d, _make_post(path)


def _make_post(path):
    message = get_file(path)
    d = _extract_date(path)
    return dict(message=message, created_time=d.strftime('%Y-%m-%dT%H:%M:%S%z'))


@pytest.fixture(params=_historical_weekly())
def historical_weekly_raw(request):
    path = request.param
    year_week = _extract_year_weeknum(path)
    files = WEEKS[year_week]
    i = max((HISTORICAL.index(p) for p in files))
    first = third = len(files) == 1 and files[0].endswith('-combined.txt')
    if not first:
        first = any(p.endswith('-first.txt') for p in files)
    if not third:
        third = any(p.endswith('-third.txt') for p in files)

    posts = (_make_post(p) for p in reversed(HISTORICAL[max(0, i-25):i+1]))
    return year_week[1], (first, third), posts
