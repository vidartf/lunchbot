#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function, unicode_literals

import re
import collections
import datetime
import locale
import logging
from pytz import timezone

from .config import config, parser, SLACK_TOKEN, FACEBOOK_SECRET, FACEBOOK_ID, SLACK_CHANNELS
from .apiwrappers import authenticated_graph, filter_messages, scrape_posts, SlackPoster


logger = logging.getLogger('lunchbot')
locale.setlocale(locale.LC_ALL, "no_NO")

floor_flags = re.IGNORECASE
patterns_first_floor = (
    r'(Meny|Menu) (uke|week) (?P<weeknum>\d+)(\D|\n)(.|\n)*?1.*?(etg|etasje|etage):?',
    r'(Meny|Menu) Transit (uke|week) (?P<weeknum>\d+):?',
)
patterns_third_floor = (
    r'Meny (uke|week) (?P<weeknum>\d+)(\D|\n)(.|\n)*?3.*?(etg|etasje|etage):?',
    r'(Meny|Menu) Expeditionen (uke|week) (?P<weeknum>\d+):?',
)

patterns_first_floor = [re.compile(p, flags=floor_flags) for p in patterns_first_floor]
patterns_third_floor = [re.compile(p, flags=floor_flags) for p in patterns_third_floor]

COMBINED_HEADER = r'((Meny(er)?|Menus?).*(uke|week)|Week|Uke).*(?P<weeknum>\d+)[^\n]*'
FIRST_FLOOR_HEADER = r'[^\n]*TRANSIT[^\n]*'
THIRD_FLOOR_HEADER = r'[^\n]*(EXPEDITI?ON(EN)?|EXPEDISJON(EN)?|EKSPEDISJON(EN)?)[^\n]*'

COMBINED_DAILY_HEADER = (
    r'(Meny(er)?|Menus?) (?P<weekday>\w+)?\s?((?P<day>\d+)\.?)\s?(?P<month>\w+)[^\n]*'
)

HEADERS = dict(
    COMBINED_HEADER=COMBINED_HEADER,
    COMBINED_DAILY_HEADER=COMBINED_DAILY_HEADER,
    FIRST_FLOOR_HEADER=FIRST_FLOOR_HEADER,
    THIRD_FLOOR_HEADER=THIRD_FLOOR_HEADER,
)

patterns_combined = (
    r'{COMBINED_HEADER}\s+'
    r'{FIRST_FLOOR_HEADER}\s*(?P<first>.*?)\s+'
    r'{THIRD_FLOOR_HEADER}\s*(?P<third>.*)',
    r'{COMBINED_HEADER}\s+'
    r'{THIRD_FLOOR_HEADER}\s*(?P<third>.*)\s+'
    r'{FIRST_FLOOR_HEADER}\s*(?P<first>.*?)',
)
combined_flags = re.IGNORECASE | re.DOTALL
patterns_combined = [
    re.compile(p.format(**HEADERS), flags=combined_flags) for p in patterns_combined
]

weekly_pattern = re.compile(COMBINED_HEADER, flags=combined_flags)

patterns_daily_combined = (
    r'{COMBINED_DAILY_HEADER}\s+'
    r'{FIRST_FLOOR_HEADER}\s*(?P<first>.*?)\s+'
    r'{THIRD_FLOOR_HEADER}\s*(?P<third>.*)',

    r'{COMBINED_DAILY_HEADER}\s+'
    r'{THIRD_FLOOR_HEADER}\s*(?P<third>.*)\s+'
    r'{FIRST_FLOOR_HEADER}\s*(?P<first>.*?)',
)
patterns_daily_combined = [
    re.compile(p.format(**HEADERS), flags=combined_flags)
    for p in patterns_daily_combined
]

patterns_daily = (
    r'{FIRST_FLOOR_HEADER}\s*(?P<first>.*?)\s+'
    r'{THIRD_FLOOR_HEADER}\s*(?P<third>.*)',

    r'{THIRD_FLOOR_HEADER}\s*(?P<third>.*)\s+'
    r'{FIRST_FLOOR_HEADER}\s*(?P<first>.*?)',
)
patterns_daily = [
    re.compile(p.format(**HEADERS), flags=combined_flags)
    for p in patterns_daily
]

pattern_days = [
    r'(MANDAG|MONDAY):?\s*(.*?)[\s\-]*\n\s*([^\n]*(TIRSDAG|TUESDAY|ONSDAG|WEDNESDAY|WENDSDAY|WEDNESAY|TORSDAG|THURSDAY|FREDAG|FRIDAY))|$',
    r'(TIRSDAG|TUESDAY):?\s*(.*?)[\s\-]*\n\s*([^\n]*(ONSDAG|WEDNESDAY|WENDSDAY"WEDNESAY|TORSDAG|THURSDAY|FREDAG|FRIDAY))|$',
    r'(ONSDAG|WEDNESDAY|WENDSDAY|WEDNESAY):?\s*(.*?)[\s\-]*\n\s*([^\n]*(TORSDAG|THURSDAY|FREDAG|FRIDAY))|$',
    r'(TORSDAG|THURSDAY):?\s*(.*?)[\s\-]*\n\s*[^\n]*((FREDAG|FRIDAY))|$',
    r'(FREDAG|FRIDAY):?\s*(.*?)[\s\-]*$',
]
days_flags = re.IGNORECASE | re.DOTALL
pattern_days = [re.compile(p, flags=combined_flags) for p in pattern_days]

Menu = collections.namedtuple('Menu', ('first', 'third', 'combined'), defaults=(None, None, None))


def run(post_menu=None):
    if None in (SLACK_TOKEN, FACEBOOK_SECRET, FACEBOOK_ID):
        raise ValueError("Missing configuration value")

    if post_menu is None:
        # Fail early for slack issues, as that is our main output channel:
        logger.info('Initializing slack client with channels %s...', SLACK_CHANNELS)
        sp = SlackPoster(SLACK_TOKEN, SLACK_CHANNELS)
        post_menu = sp.post

    menu = Menu()

    try:
        # logger.info('Initializing Facebook graph API...')
        # graph = authenticated_graph(FACEBOOK_ID, FACEBOOK_SECRET)

        logger.info('Getting facebook posts...')
        # posts = graph.get('technopolisitfornebu/published_posts')['data']
        posts = scrape_posts("technopolisitfornebu")

        menu = get_menus(posts, datetime.datetime.now(timezone('Europe/Oslo')))
    finally:
        if menu.first:
            post_menu('*First floor menu:*\n' + menu.first)
        if menu.third:
            post_menu('*Third floor menu:*\n' + menu.third)
        if menu.combined and not (menu.first or menu.third):
            post_menu("*Today's menu:*\n" + menu.combined)
        else:
            # not combined, post a single sad message
            if not menu.first and not menu.third:
                post_menu(
                    '_Could not find a menu for today_ :disappointed:'
                )
            if menu.first and not menu.third:
                post_menu(
                    '_Could not find a menu for the third floor today_ :disappointed:'
                )
            elif menu.third and not menu.first:
                post_menu(
                    '_Could not find a menu for the first floor today_ :disappointed:'
                )


def filter_msg_distance(posts, ref, days):
    """Filter any message by distance from a reference"""
    for post in posts:
        msg_dt = datetime.datetime.strptime(post['created_time'], '%Y-%m-%dT%H:%M:%S%z')
        if abs(msg_dt - ref).days <= days:
            logger.info("checking post from: {}".format(post['created_time']))
            logger.debug(' '.join(post['message'].lstrip().splitlines()[:1]))
            yield post
        else:
            logger.debug("ignoring post from: {}".format(post['created_time']))
            logger.debug(' '.join(post['message'].lstrip().splitlines()[:1]))


def localized_month(monthstr):
    try:
        return datetime.datetime.strptime(monthstr, "%B").month
    except ValueError:
        return None


def get_menus(posts, date):
    """Get the menu for the given date."""
    # First, try daily menu:
    posts = list(filter_msg_distance(filter_messages(posts), date, 14))
    menu = get_menus_for_day(posts, date)
    if menu:
        return menu

    # Then, check for weekly menu
    week_number = date.isocalendar()[1]

    logger.info("No daily menu, checking for week {}".format(week_number))
    menus = get_menus_for_week(posts, week_number)
    weekday = date.weekday()
    if weekday < 5:
        return menus[weekday]
    else:
        return Menu()


def get_menus_for_day(posts, date):
    """Get the menu for the given date matching daily menu."""
    # First, try daily menu:
    day = date.day
    month = date.month

    for post in posts:
        message = post['message']
        for pattern in patterns_daily_combined:
            match = pattern.search(message)
            if (
                match is not None
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
    # first, find the post with a likely weekly menu
    for post in posts:
        message = post['message']
        match = weekly_pattern.search(message)
        if match:
            logger.warning("Found likely weekly menu from %s", post['created_time'])
            break
    else:
        logger.warning('No weekly menu found!')
        return [Menu() for i in range(5)]

    for pattern in patterns_combined:
        match = pattern.search(message)
        if match is not None and int(match.group('weeknum')) == week_number:
            logger.info('Found post that matches a combined menu for this week')
            week_first, week_third = match.group('first', 'third')
            menu_first_floor = extract_menu(week_first)
            menu_third_floor = extract_menu(week_third)
            return [Menu(first=first, third=third) for first, third in zip(menu_first_floor, menu_third_floor)]

    # weekly menu, by day first, not floor
    menus = []
    for combined in extract_menu(message):
        for pattern in patterns_daily:
            match = pattern.search(combined)
            if not match:
                continue
            first, third = match.group('first', 'third')
            if first and third:
                combined = None
                break
        menus.append(Menu(first=first, third=third, combined=combined))
    return menus


def is_matching_message(message, floor_patterns, week_number):
    """Check if a message conatins a menu for given floor pattern and week number"""
    for floor_pattern in floor_patterns:
        week_match = floor_pattern.search(message)
        if week_match is not None and int(week_match.group('weeknum')) == week_number:
            return True
    return False


def trim_multiline(text):
    return '\n'.join(line.strip() for line in text.splitlines())


def extract_menu(message):
    """Extract the menu from a message"""
    menu = [None] * 5
    for day in range(5):
        match = pattern_days[day].search(message)
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
