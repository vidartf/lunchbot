#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function, unicode_literals

import re
import datetime
import logging

from .config import config, parser, SLACK_TOKEN, FACEBOOK_SECRET, FACEBOOK_ID
from .apiwrappers import authenticated_graph, filter_messages, SlackPoster


logger = logging.getLogger('lunchbot')

# Where to post:
channels = ['lunch', 'lunchbotdev']

patterns_first_floor = (r'(Meny|Menu) (uke|week) (?P<weeknum>\d+)\D.*?1.*?(etg|etasje|etage)',
    r'(Meny|Menu) Expeditionen (uke|week) (?P<weeknum>\d+):?')
patterns_third_floor = (r'Meny (uke|week) (?P<weeknum>\d+)\D.*?3.*?(etg|etasje|etage)',
    r'(Meny|Menu) Transit (uke|week) (?P<weeknum>\d+):?')
patterns_combined = (
    r'(Meny|Menu) (uke|week) (?P<weeknum>\d+)[^\n]*\n+'
    r'GATE 1 & 2 \(TRANSIT,? 1st FLOOR\)\n*(?P<first>.*?)\n+'
    r'(EXPEDITIONEN|EXPEDITONEN|EXPEDISJON) \(3rd FLOOR\)\n*(?P<third>.*)',

    r'(Meny|Menu) (uke|week) (?P<weeknum>\d+)[^\n]*\n+'
    r'TRANSIT,.*?1.*?(etg|etasje|etage)\n*(?P<first>.*?)\n+'
    r'(EXPEDITIONEN|EXPEDITONEN|EXPEDISJON).*?3.*?(etg|etasje|etage)\n*(?P<third>.*)',
    )
floor_flags = re.IGNORECASE
combined_flags = re.IGNORECASE | re.DOTALL

pattern_days = [
    r'(MANDAG|MONDAY):?\n?(.*?)\n*(TIRSDAG|TUESDAY|ONSDAG|WEDNESDAY|WENDSDAY|WEDNESAY|TORSDAG|THURSDAY|FREDAG|FRIDAY)|$',
    r'(TIRSDAG|TUESDAY):?\n?(.*?)\n*(ONSDAG|WEDNESDAY|WENDSDAY"WEDNESAY|TORSDAG|THURSDAY|FREDAG|FRIDAY)|$',
    r'(ONSDAG|WEDNESDAY|WENDSDAY|WEDNESAY):?\n?(.*?)\n*(TORSDAG|THURSDAY|FREDAG|FRIDAY)|$',
    r'(TORSDAG|THURSDAY):?\n?(.*?)\n*(FREDAG|FRIDAY)|$',
    r'(FREDAG|FRIDAY):?\n?(.*?)\n*$'
]
days_flags = re.IGNORECASE | re.DOTALL


def run(post_menu=None):
    if None in (SLACK_TOKEN, FACEBOOK_SECRET, FACEBOOK_ID):
        raise ValueError("Missing configuration value")

    if post_menu is None:
        # Fail early for slack issues, as that is our main output channel:
        logger.info('Initializing slack client...')
        sp = SlackPoster(SLACK_TOKEN, channels)
        post_menu = sp.post

    menu_first_floor = None
    menu_third_floor = None

    try:
        logger.info('Initializing Facebook graph API...')
        graph = authenticated_graph(FACEBOOK_ID, FACEBOOK_SECRET)

        logger.info('Getting facebook posts...')
        posts = graph.get('technopolisitfornebu/posts')

        week_number = datetime.datetime.today().isocalendar()[1]
        menu_first_floor, menu_third_floor = get_menus_for_week(
            filter_messages(posts),
            week_number
        )

    finally:
        day = datetime.datetime.today().weekday()
        if day < 5:
            if menu_first_floor and menu_first_floor[day]:
                post_menu('*First floor menu:*\n' + menu_first_floor[day])
            else:
                post_menu('_Could not find a menu for the first floor today_ :disappointed:')
            if menu_third_floor and menu_third_floor[day]:
                post_menu('*Third floor menu:*\n' + menu_third_floor[day])
            else:
                post_menu('_Could not find a menu for the third floor today_ :disappointed:')


def get_menus_for_week(posts, week_number):
    """Get the menu for the given week number."""
    menu_first_floor = None
    menu_third_floor = None
    for post in posts:
        # time = post['created_time']
        message = post['message']

        if menu_first_floor is None and is_matching_message(message, patterns_first_floor, week_number):
            logger.info('Found post that matches first floor menu for this week')
            menu_first_floor = extract_menu(message)
        elif menu_third_floor is None and is_matching_message(message, patterns_third_floor, week_number):
            logger.info('Found post that matches third floor menu for this week')
            menu_third_floor = extract_menu(message)
        elif (menu_first_floor is None and menu_third_floor is None):
            for pattern in patterns_combined:
                match = re.match(pattern, message, flags=combined_flags)
                if match is not None and int(match.group('weeknum')) == week_number:
                    logger.info('Found post that matches a combined menu for this week')
                    week_first, week_third = match.group('first', 'third')
                    menu_first_floor = extract_menu(week_first)
                    menu_third_floor = extract_menu(week_third)
                    break
            else:
                logger.debug('Not a menu for week %d:\n%s', week_number, message)
        else:
            logger.debug('Not a menu for week %d:\n%s', week_number, message)

        if menu_first_floor is not None and menu_third_floor is not None:
            break
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


def extract_menu(message):
    """Extract the menu from a message"""
    menu = [None] * 5
    for day in range(5):
        match = re.search(pattern_days[day], message, flags=days_flags)
        if match and match.group(2):
            logger.info('Found menu for day %d', day)
            logger.debug(match.groups())
            menu[day] = match.group(2)
        else:
            logger.warning('Could not find menu for day %d. Match: %s', day, match.groups())
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
