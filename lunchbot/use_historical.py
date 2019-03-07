#!/usr/bin/env python
# coding: utf-8

import io
import os
import glob
from datetime import datetime, date, timedelta
from collections import defaultdict, namedtuple
import re
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

from pytz import timezone
import pytest

from .main import extract_menu, patterns_combined, combined_flags

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
    '161216-third.txt': (4,),
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


def historical():
    dirname = os.path.join(here,  'historical')
    filenames = glob.glob(os.path.join(dirname, "*.txt"))
    return (fn for fn in filenames)

HISTORICAL = tuple(sorted(historical()))


def first_floor():
    for fn in historical():
        if fn.endswith('-first.txt'):
            yield fn


def third_floor():
    for fn in historical():
        if fn.endswith('-third.txt'):
            yield fn

def combined():
    for fn in historical():
        if fn.endswith('-combined.txt'):
            yield fn

def historical_weekly():
    for fn in historical():
        if not fn.endswith('-dailycomb.txt'):
            yield fn

def daily_combined():
    for fn in historical():
        if fn.endswith('-dailycomb.txt'):
            yield fn

def weeks():
    lut = defaultdict(list)
    for fn in historical():
        if fn.endswith('-dailycomb.txt'):
            continue
        year_week = extract_year_weeknum(fn)
        lut[year_week].append(fn)
        assert len(lut[year_week]) <= 2
    return lut




@lru_cache(256)
def extract_year_weeknum(path):
    filename = os.path.basename(path)
    if filename in weeknum_override:
        return weeknum_override[filename]
    filename = os.path.splitext(filename)[0]
    d = datetime.strptime(filename.split('-')[0], '%y%m%d')
    return d.isocalendar()[:2]


def extract_week_num(path):
    return extract_year_weeknum(path)[1]

def extract_date(path):
    filename = os.path.basename(path)
    if filename in date_override:
        return datetime(*date_override[filename], tzinfo=timezone('Europe/Oslo'))
    filename = os.path.splitext(filename)[0]
    d = datetime.strptime(filename.split('-')[0], '%y%m%d')
    return d.replace(tzinfo=timezone('Europe/Oslo'))


def _iso_year_start(iso_year):
    "The gregorian calendar date of the first day of the given ISO year"
    fourth_jan = date(iso_year, 1, 4)
    delta = timedelta(fourth_jan.isoweekday()-1)
    return fourth_jan - delta

def _iso_to_gregorian(iso_year, iso_week, iso_day):
    "Gregorian calendar date for the given ISO year, week and day"
    year_start = _iso_year_start(iso_year)
    return year_start + timedelta(days=iso_day-1, weeks=iso_week-1)


WEEKS = weeks()


def split_combined(message):
    for pattern in patterns_combined:
        match = re.match(pattern, message, flags=combined_flags)
        if match is not None:
            return match.group('first', 'third')

    return [message]

def is_missing(path, floornum, daynum):
    entry = known_missing.get(os.path.basename(path), None)
    if not entry:
        return False
    if not isinstance(entry, list):
        entry = [entry, entry]
    return daynum in entry[floornum]

invalid_entry_cutoff = date(2016, 7, 1)

Entry = namedtuple('Entry', ('menu', 'date', 'floor'))

def iter_menus():
    floor_names = ['first', 'third']
    for fn in historical_weekly():
        if fn.endswith('190114-first.txt'):
            continue
        week_menu = get_file(fn)
        year, weeknum = extract_year_weeknum(fn)
        for floor, floor_menu in enumerate(split_combined(week_menu)):
            for day_num, daily in enumerate(extract_menu(floor_menu)):
                if daily is None or is_missing(fn, floor, day_num):
                    continue
                d = _iso_to_gregorian(year, weeknum, day_num)
                if d > invalid_entry_cutoff:
                    yield Entry(menu=daily, date=d, floor=floor_names[floor])
