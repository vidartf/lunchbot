#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function, unicode_literals

import re
import collections
import datetime
import locale
import logging
from pytz import timezone

from .config import config, parser, SLACK_TOKEN, FACEBOOK_SECRET, FACEBOOK_ID
from .apiwrappers import authenticated_graph, filter_messages, SlackPoster


logger = logging.getLogger('lunchbot')
locale.setlocale(locale.LC_ALL, "nb_NO.utf8")

# Where to post:
channels = ['lunch', 'lunchbotdev']


patterns_first_floor = (r'(Meny|Menu) (uke|week) (?P<weeknum>\d+)(\D|\n)(.|\n)*?1.*?(etg|etasje|etage):?',
    r'(Meny|Menu) Transit (uke|week) (?P<weeknum>\d+):?')
patterns_third_floor = (r'Meny (uke|week) (?P<weeknum>\d+)(\D|\n)(.|\n)*?3.*?(etg|etasje|etage):?',
    r'(Meny|Menu) Expeditionen (uke|week) (?P<weeknum>\d+):?')
COMBINED_HEADER = r'((Meny(er)?|Menus?) (uke|week)|Week|Uke) (?P<weeknum>\d+)[^\n]*'
FIRST_FLOOR_HEADER_A = r'GATE 1 & 2 \(TRANSIT,? 1st FLOOR\):?'
FIRST_FLOOR_HEADER_B = r'.{0,5}?TRANSIT(.*?1.*?(etg|etasje|etage))?:?'
THIRD_FLOOR_HEADER_A = r'[^\n]*(EXPEDITI?ON(EN)?|EXPEDISJON(EN)?|Ekspedisjon(en)?) \(3rd FLOOR\):?'
THIRD_FLOOR_HEADER_B = r'[^\n]*(EXPEDITI?ON(EN)?|EXPEDISJON(EN)?|Ekspedisjon(en)?)(.*?3.*?(etg|etasje|etage))?:?'

COMBINED_DAILY_HEADER = r'(Meny(er)?|Menus?) (?P<weekday>\w+)?\s?((?P<day>\d+)\.?)\s?(?P<month>\w+)[^\n]*'

HEADERS = dict(
    COMBINED_HEADER=COMBINED_HEADER,
    COMBINED_DAILY_HEADER=COMBINED_DAILY_HEADER,
    FIRST_FLOOR_HEADER_A=FIRST_FLOOR_HEADER_A,
    FIRST_FLOOR_HEADER_B=FIRST_FLOOR_HEADER_B,
    THIRD_FLOOR_HEADER_A=THIRD_FLOOR_HEADER_A,
    THIRD_FLOOR_HEADER_B=THIRD_FLOOR_HEADER_B,
    )

patterns_combined = (
    r'{COMBINED_HEADER}\s+'
    r'{FIRST_FLOOR_HEADER_A}\s*(?P<first>.*?)\s+'
    r'{THIRD_FLOOR_HEADER_A}\s*(?P<third>.*)',

    r'{COMBINED_HEADER}\s+'
    r'{FIRST_FLOOR_HEADER_B}\s*(?P<first>.*?)\s+'
    r'{THIRD_FLOOR_HEADER_B}\s*(?P<third>.*)',

    r'{COMBINED_HEADER}\s+'
    r'{THIRD_FLOOR_HEADER_A}\s*(?P<third>.*?)\s+'
    r'{FIRST_FLOOR_HEADER_A}\s*(?P<first>.*)',

    r'{COMBINED_HEADER}\s+'
    r'{THIRD_FLOOR_HEADER_B}\s*(?P<third>.*?)\s+'
    r'{FIRST_FLOOR_HEADER_B}\s*(?P<first>.*)',
    )
patterns_combined = [p.format(**HEADERS) for p in patterns_combined]
floor_flags = re.IGNORECASE
combined_flags = re.IGNORECASE | re.DOTALL

patterns_daily_combined = (
    r'{COMBINED_DAILY_HEADER}\s+'
    r'{FIRST_FLOOR_HEADER_A}\s*(?P<first>.*?)\s+'
    r'{THIRD_FLOOR_HEADER_A}\s*(?P<third>.*)',

    r'{COMBINED_DAILY_HEADER}\s+'
    r'{FIRST_FLOOR_HEADER_B}\s*(?P<first>.*?)\s+'
    r'{THIRD_FLOOR_HEADER_B}\s*(?P<third>.*)',

    r'{COMBINED_DAILY_HEADER}\s+'
    r'{THIRD_FLOOR_HEADER_A}\s*(?P<third>.*?)\s+'
    r'{FIRST_FLOOR_HEADER_A}\s*(?P<first>.*)',

    r'{COMBINED_DAILY_HEADER}\s+'
    r'{THIRD_FLOOR_HEADER_B}\s*(?P<third>.*?)\s+'
    r'{FIRST_FLOOR_HEADER_B}\s*(?P<first>.*)',
)
patterns_daily_combined = [p.format(**HEADERS) for p in patterns_daily_combined]

patterns_headerless_combined = (
    r'{FIRST_FLOOR_HEADER_A}\s*(?P<first>.*?)\s+'
    r'{THIRD_FLOOR_HEADER_A}\s*(?P<third>.*)',

    r'{FIRST_FLOOR_HEADER_B}\s*(?P<first>.*?)\s+'
    r'{THIRD_FLOOR_HEADER_B}\s*(?P<third>.*)',

    r'{THIRD_FLOOR_HEADER_A}\s*(?P<third>.*?)\s+'
    r'{FIRST_FLOOR_HEADER_A}\s*(?P<first>.*)',

    r'{THIRD_FLOOR_HEADER_B}\s*(?P<third>.*?)\s+'
    r'{FIRST_FLOOR_HEADER_B}\s*(?P<first>.*)',
    )
patterns_headerless_combined = [p.format(**HEADERS) for p in patterns_headerless_combined]

pattern_days = [
    r'(MANDAG|MONDAY):?\s*(.*?)\s*\n\s*([^\n]*(TIRSDAG|TUESDAY|ONSDAG|WEDNESDAY|WENDSDAY|WEDNESAY|TORSDAG|THURSDAY|FREDAG|FRIDAY))|$',
    r'(TIRSDAG|TUESDAY):?\s*(.*?)\s*\n\s*([^\n]*(ONSDAG|WEDNESDAY|WENDSDAY"WEDNESAY|TORSDAG|THURSDAY|FREDAG|FRIDAY))|$',
    r'(ONSDAG|WEDNESDAY|WENDSDAY|WEDNESAY):?\s*(.*?)\s*\n\s*([^\n]*(TORSDAG|THURSDAY|FREDAG|FRIDAY))|$',
    r'(TORSDAG|THURSDAY):?\s*(.*?)\s*\n\s*[^\n]*((FREDAG|FRIDAY))|$',
    r'(FREDAG|FRIDAY):?\s*(.*?)\s*$'
]
days_flags = re.IGNORECASE | re.DOTALL


Menu = collections.namedtuple('Menu', ('first', 'third'))


def run(post_menu=None):
    if None in (SLACK_TOKEN, FACEBOOK_SECRET, FACEBOOK_ID):
        raise ValueError("Missing configuration value")

    if post_menu is None:
        # Fail early for slack issues, as that is our main output channel:
        logger.info('Initializing slack client...')
        sp = SlackPoster(SLACK_TOKEN, channels)
        post_menu = sp.post

    menu = Menu(None, None)

    try:
        logger.info('Initializing Facebook graph API...')
        graph = authenticated_graph(FACEBOOK_ID, FACEBOOK_SECRET)

        logger.info('Getting facebook posts...')
        posts = graph.get('technopolisitfornebu/posts')

        menu = get_menus(posts, datetime.datetime.now(timezone('Europe/Oslo')))
    finally:
        if menu.first:
            post_menu('*First floor menu:*\n' + menu.first)
        else:
            post_menu('_Could not find a menu for the first floor today_ :disappointed:')
        if menu.third:
            post_menu('*Third floor menu:*\n' + menu.third)
        else:
            post_menu('_Could not find a menu for the third floor today_ :disappointed:')


def msg_time_distance(created_time, ref):
    """Measure time distance (in days) from a reference"""
    msg_dt = datetime.datetime.strptime(
        created_time,
        '%Y-%m-%dT%H:%M:%S%z'
    )
    return abs(msg_dt - ref).days


def filter_msg_distance(posts, ref, days):
    """Filter any message by distance from a reference"""
    for post in posts:
        if msg_time_distance(post['created_time'], ref) <= days:
            yield post


def localized_month(monthstr):
    try:
        return datetime.datetime.strptime(monthstr, "%B").month
    except ValueError:
        return None


def get_menus(posts, date):
    """Get the menu for the given date."""
    # First, try daily menu:
    menu = get_menus_for_day(posts, date)
    if menu:
        return menu

    # Then, check for weekly menu
    week_number = date.isocalendar()[1]
    menu_first_floor, menu_third_floor = get_menus_for_week(
        filter_messages(posts),
        week_number
    )
    menus = [None, None]
    if menu_first_floor or menu_third_floor:
        weekday = date.weekday()
        if weekday < 5:
            if menu_first_floor and menu_first_floor[weekday]:
                menus[0] = menu_first_floor[weekday]
            if menu_third_floor and menu_third_floor[weekday]:
                menus[1] = menu_third_floor[weekday]

    return Menu(*menus)


def get_menus_for_day(posts, date):
    """Get the menu for the given date matching daily menu."""
    # First, try daily menu:
    day = date.day
    month = date.month
    year = date.year

    for post in filter_msg_distance(filter_messages(posts), date, 10):
        message = post['message']
        for pattern in patterns_daily_combined:
            match = re.match(pattern, message, flags=combined_flags)
            if (match is not None
                and localized_month(match.group('month')) == month
                and int(match.group('day')) == day
            ):
                logger.info('Found post that matches a combined menu for this day')
                logger.debug(message)
                first, third = match.group('first', 'third')
                return Menu(trim_multiline(first), trim_multiline(third))

    return None


def get_menus_for_week(posts, week_number):
    """Get the menu for the given week number."""
    menu_first_floor = None
    menu_third_floor = None
    for post in posts:
        time = post['created_time']
        message = post['message']
        if (menu_first_floor is None and menu_third_floor is None):
            for pattern in patterns_combined:
                match = re.match(pattern, message, flags=combined_flags)
                if match is not None and int(match.group('weeknum')) == week_number:
                    logger.info('Found post that matches a combined menu for this week')
                    week_first, week_third = match.group('first', 'third')
                    menu_first_floor = extract_menu(week_first)
                    menu_third_floor = extract_menu(week_third)
                    return menu_first_floor, menu_third_floor
            else:
                logger.debug('Not a combined menu for week %d:\n%s', week_number, message)

        if menu_first_floor is None and is_matching_message(message, patterns_first_floor, week_number):
            logger.info('Found post that matches first floor menu for this week')
            menu_first_floor = extract_menu(message)
        elif menu_third_floor is None and is_matching_message(message, patterns_third_floor, week_number):
            logger.info('Found post that matches third floor menu for this week')
            menu_third_floor = extract_menu(message)
        else:
            if menu_first_floor is None and menu_third_floor is None:
                menu_first_floor, menu_third_floor = extract_headerless_week_menu(message, time)
                if menu_first_floor and menu_third_floor:
                    return menu_first_floor, menu_third_floor
                logger.debug('Not a menu for week %d:\n%s', week_number, message)

        if menu_first_floor is not None and menu_third_floor is not None:
            break
    else:
        logger.warning('No posts to process!')
    return menu_first_floor, menu_third_floor


def is_matching_message(message, floor_patterns, week_number, flags=None):
    """Check if a message conatins a menu for given floor pattern and week number"""
    if flags is None:
        flags = floor_flags
    for floor_pattern in floor_patterns:
        week_match = re.match(floor_pattern, message, flags=flags)
        if week_match is not None and int(week_match.group('weeknum')) == week_number:
            return True
    return False


def extract_headerless_week_menu(message, time):
    date = datetime.datetime.now(timezone('Europe/Oslo'))
    menu_first_floor = None
    menu_third_floor = None

    if msg_time_distance(time, date) <= 5 + date.weekday():
        for pattern in patterns_headerless_combined:
            match = re.match(pattern, message, flags=combined_flags)
            if match:
                week_first, week_third = match.group('first', 'third')
                menu_first_floor = extract_menu(week_first)
                menu_third_floor = extract_menu(week_third)

                if None in menu_first_floor or None in menu_third_floor:
                    # Menu for the full week must be found.
                    menu_first_floor = None
                    menu_third_floor = None
                    continue
                return menu_first_floor, menu_third_floor

    return menu_first_floor, menu_third_floor


def trim_multiline(text):
    return '\n'.join(line.strip() for line in text.splitlines())


def extract_menu(message):
    """Extract the menu from a message"""
    menu = [None] * 5
    for day in range(5):
        match = re.search(pattern_days[day], message, flags=days_flags)
        if match and match.group(2):
            logger.info('Found menu for day %d', day)
            logger.debug(match.groups())
            menu[day] = trim_multiline(match.group(2))
        else:
            logger.warning('Could not find menu for day %d.', day)
            if match:
                logger.warning('Match: %s', match.groups())
            logger.warning('Message: %r', message)
    return menu


def main(args=None, post_menu=None):
    # Set up logging:
    arguments = parser.parse_args(args)
    if arguments.verbose:
        loglevel = 'DEBUG'
    else:
        loglevel = config.get('General', 'log-level', fallback='INFO')
    logging.basicConfig(level=loglevel)

    run(post_menu=post_menu)

if __name__ == '__main__':
    main()
