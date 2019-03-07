#!/usr/bin/env python
# coding: utf-8

"""Run script against historical data"""

import re

from lunchbot.main import (
    is_matching_message,
    extract_menu,
    get_menus_for_week,
    get_menus_for_day,
    patterns_first_floor,
    patterns_third_floor,
    patterns_combined,
    patterns_daily_combined,
    combined_flags
)

from lunchbot.use_historical import (
    split_combined
)

pattern_daynames = re.compile(r'MANDAG|TIRSDAG|ONSDAG|TORSDAG|FREDAG|MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY')



def test_extract_menu(historical_weekly):
    message, known_missing = historical_weekly
    if known_missing and not isinstance(known_missing, list):
        known_missing = [known_missing, known_missing]
    raws = split_combined(message)
    for i, raw in enumerate(raws):
        if raw is None:
            continue
        menu = extract_menu(raw)
        for day, entry in enumerate(menu):
            if known_missing and day in known_missing[i]:
                # Skip days that we know were not included in menus
                continue
            # Assert that the menu was found
            assert entry is not None, "No menu entry found for day %d" % day
            # Assert that there was no "bleedover" between days
            assert not re.match(pattern_daynames, entry)


def test_first_floor_match(historical_first_floor):
    week_num, message = historical_first_floor
    assert is_matching_message(message, patterns_first_floor, week_num)


def test_third_floor_match(historical_third_floor):
    week_num, message = historical_third_floor
    assert is_matching_message(message, patterns_third_floor, week_num)

def test_combined_match(historical_combined):
    week_num, message = historical_combined
    assert is_matching_message(message, patterns_combined, week_num, combined_flags)

def test_daily_sanity(historical_daily_post):
    date, post = historical_daily_post
    menu = get_menus_for_day({'data': [post]}, date)
    assert menu is not None
    assert menu.first
    assert menu.third


def test_menus_for_week(historical_weekly_raw, request):
    weeknum, expected, posts = historical_weekly_raw
    result = get_menus_for_week(posts, weeknum)
    assert (result[0] is not None) == expected[0]
    assert (result[1] is not None) == expected[1]
