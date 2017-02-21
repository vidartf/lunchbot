#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function, unicode_literals

import re
import os
import datetime
import configparser
import logging
import argparse

from slackclient import SlackClient
from facepy import GraphAPI

parser = argparse.ArgumentParser(
    description='A bot for slack that fetches and parses the lunch menu for Technopolis IT Fornebu'
)
parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")
arguments = parser.parse_args()

here = os.path.abspath(os.path.dirname(__file__))
logger = logging.getLogger('lunchbot')

config = configparser.SafeConfigParser()
files = config.read([
    './lunchbot.ini',
    os.path.join(here, 'lunchbot.ini'),
    os.path.expanduser('~/lunchbot.ini'),
    os.path.expanduser('~/.lunchbot.rc')])

SLACK_TOKEN = config.get(
    'Slack', 'token',
    fallback=os.environ.get("SLACK_API_TOKEN", None))
FACEBOOK_SECRET = config.get(
    'Facebook', 'secret',
    fallback=os.environ.get("FACEBOOK_API_SECRET", None))
FACEBOOK_ID = config.get(
    'Facebook', 'id',
    fallback=os.environ.get("FACEBOOK_API_ID", None))

if None in (SLACK_TOKEN, FACEBOOK_SECRET, FACEBOOK_ID):
    raise ValueError("Missing configuration value")

if arguments.verbose:
    loglevel = 'DEBUG'
else:
    loglevel = config.get('General', 'log-level', fallback='INFO')
logging.basicConfig(level=loglevel)


logger.info('Initializing slack client...')
sc = SlackClient(SLACK_TOKEN)

channels = ['lunch', 'lunchbotdev']


def post_menu(menu_message):
    for ch in channels:
        sc.api_call(
            'chat.postMessage',
            channel=ch,
            text=menu_message,
            as_user=False,
            username='lunchbot',
            icon_emoji=':spaghetti:'
        )


def get_facebook_token(id, secret):
    graph = GraphAPI()
    request = 'oauth/access_token?client_id=%s&client_secret=%s&grant_type=client_credentials'
    token = graph.get(request % (id, secret))
    # Remove prefix:
    return token.replace('access_token=', '')


try:
    # Initialize the Graph API with a valid access facebook_token (optional,
    # but will allow you to do all sorts of fun stuff).
    logger.info('Initializing Facebook graph API...')
    facebook_token = get_facebook_token(FACEBOOK_ID, FACEBOOK_SECRET)
    graph = GraphAPI(facebook_token)

    # Get my latest posts
    logger.info('Getting facebook posts...')
    posts = graph.get('technopolisitfornebu/posts')
    data = posts['data']

    pattern_first_floor = r'Meny uke (\d+),.*1.*(etg|etasje|etage)'
    pattern_third_floor = r'Meny uke (\d+),.*3.*(etg|etasje|etage)'
    pattern_days = [
        r'(MANDAG|MONDAY)\n?(.*?)\n*(TIRSDAG|TUESDAY|ONSDAG|WEDNESDAY|WENDSDAY|TORSDAG|THURSDAY|FREDAG|FRIDAY)|$',
        r'(TIRSDAG|TUESDAY)\n?(.*?)\n*(ONSDAG|WEDNESDAY|WENDSDAY|TORSDAG|THURSDAY|FREDAG|FRIDAY)|$',
        r'(ONSDAG|WEDNESDAY|WENDSDAY)\n?(.*?)\n*(TORSDAG|THURSDAY|FREDAG|FRIDAY)|$',
        r'(TORSDAG|THURSDAY)\n?(.*?)\n*(FREDAG|FRIDAY)|$',
        r'(FREDAG|FRIDAY)\n?(.*?)\n*$'
    ]

    menu_first_floor = None
    menu_third_floor = None

    week_number = datetime.datetime.today().isocalendar()[1]

    for post in data:
        time = post['created_time']
        if 'message' not in post:
            continue
        message = post['message']

        week_match_first = re.match(pattern_first_floor, message, flags=re.IGNORECASE)
        week_match_third = re.match(pattern_third_floor, message, flags=re.IGNORECASE)
        if menu_first_floor is None and week_match_first is not None and int(week_match_first.group(1)) == week_number:
            logger.info('Found post that matches first floor menu for this week')
            menu_first_floor = [None] * 5
            for day in range(5):
                match = re.search(pattern_days[day], message, flags=re.IGNORECASE | re.DOTALL)
                if match and match.group(2):
                    logger.info('Found menu for day %d' % day)
                    logger.debug(match.groups())
                    menu_first_floor[day] = match.group(2)
                else:
                    logger.warning('Could not find menu for day %d. Match: %s' % (day, match.groups()))
                    logger.warning('Message: %r' % message)
        elif menu_third_floor is None and week_match_third is not None and int(week_match_third.group(1)) == week_number:
            logger.info('Found post that matches third floor menu for this week')
            menu_third_floor = [None] * 5
            for day in range(5):
                match = re.search(pattern_days[day], message, flags=re.IGNORECASE | re.DOTALL)
                if match and match.group(2):
                    logger.info('Found menu for day %d' % day)
                    logger.debug(match.groups())
                    menu_third_floor[day] = match.group(2)
                else:
                    logger.warning('Could not find menu for day %d. Match: %s' % (day, match))
                    logger.warning('Message: %s' % message)

        if menu_first_floor is not None and menu_third_floor is not None:
            break

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
