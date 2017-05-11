#!/usr/bin/env python
# coding: utf-8

"""Run script against historical data"""

import re

from lunchbot.main import (
    is_matching_message, extract_menu, get_menus_for_week,
    pattern_first_floor, pattern_third_floor)


pattern_daynames = re.compile(r'MANDAG|TIRSDAG|ONSDAG|TORSDAG|FREDAG|MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY')


def test_extract_menu(historical):
    message, known_missing = historical
    menu = extract_menu(message)
    for day, entry in enumerate(menu):
        if known_missing and day in known_missing:
            # Skip days that we know were not included in menus
            continue
        # Assert that the menu was found
        assert entry is not None, "No menu entry found for day %d" % day
        # Assert that there was no "bleedover" between days
        assert not re.match(pattern_daynames, entry)


def test_first_floor_match(historical_first_floor):
    week_num, message = historical_first_floor
    assert is_matching_message(message, pattern_first_floor, week_num)


def test_third_floor_match(historical_third_floor):
    week_num, message = historical_third_floor
    assert is_matching_message(message, pattern_third_floor, week_num)
