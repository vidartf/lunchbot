#!/usr/bin/env python
# coding: utf-8

import os
import pytest

from ..use_historical import (
    historical_weekly as _weekly,
    first_floor,
    third_floor,
    combined,
    daily_combined,
    extract_year_weeknum,
    extract_week_num,
    extract_date,
    get_file,
    known_missing,
    WEEKS,
    HISTORICAL,
)

@pytest.fixture(params=_weekly())
def historical_weekly(request):
    path = request.param
    filename = os.path.basename(path)
    missing = known_missing.get(filename)
    return get_file(path), missing


@pytest.fixture(params=first_floor())
def historical_first_floor(request):
    path = request.param
    week_num = extract_week_num(path)
    return week_num, get_file(path)


@pytest.fixture(params=third_floor())
def historical_third_floor(request):
    path = request.param
    week_num = extract_week_num(path)
    return week_num, get_file(path)


@pytest.fixture(params=combined())
def historical_combined(request):
    path = request.param
    week_num = extract_week_num(path)
    return week_num, get_file(path)


@pytest.fixture(params=daily_combined())
def historical_daily_post(request):
    path = request.param
    d = extract_date(path)
    return d, _make_post(path)


def _make_post(path):
    message = get_file(path)
    d = extract_date(path)
    return dict(message=message, created_time=d.strftime('%Y-%m-%dT%H:%M:%S%z'))


@pytest.fixture(params=_weekly())
def historical_weekly_raw(request):
    path = request.param
    year_week = extract_year_weeknum(path)
    files = WEEKS[year_week]
    i = max((HISTORICAL.index(p) for p in files))
    first = third = len(files) == 1 and files[0].endswith('-combined.txt')
    if not first:
        first = any(p.endswith('-first.txt') for p in files)
    if not third:
        third = any(p.endswith('-third.txt') for p in files)

    posts = (_make_post(p) for p in reversed(HISTORICAL[max(0, i-25):i+1]))
    return year_week[1], (first, third), posts
