#!/usr/bin/env python
# coding: utf-8

import re
import os
import datetime
import configparser

from slackclient import SlackClient
from facepy import GraphAPI

here = os.path.abspath(os.path.dirname(__file__))

config = configparser.SafeConfigParser()
files = config.read(['./lunchbot.ini', os.path.join(here, 'lunchbot.ini'), '~/lunchbot.ini', '~/.lunchbot.rc'])

SLACK_TOKEN = config.get('Slack', 'token', fallback=os.environ.get("SLACK_API_TOKEN", None))
FACEBOOK_SECRET = config.get('Facebook', 'secret', fallback=os.environ.get("FACEBOOK_API_SECRET", None))
FACEBOOK_ID = config.get('Facebook', 'id', fallback=os.environ.get("FACEBOOK_API_ID", None))

if None in (SLACK_TOKEN, FACEBOOK_SECRET, FACEBOOK_ID):
    raise ValueError("Missing configuration value")



sc = SlackClient(SLACK_TOKEN)

channels = ['biocomp', 'lunchbotdev']

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
    facebook_token = get_facebook_token(FACEBOOK_ID, FACEBOOK_SECRET)
    graph = GraphAPI(facebook_token)

    # Get my latest posts
    posts = graph.get('technopolisitfornebu/posts')
    data = posts['data']

    pattern_third_floor = 'Meny uke (\d+), Expeditionen'
    pattern_first_floor = 'Meny uke (\d+), Transit'
    pattern_days = 'MANDAG\n(.*)\n*TIRSDAG\n(.*)\n*ONSDAG\n(.*)\n*TORSDAG\n(.*)\n*FREDAG\n(.*)\n*'

    menu_first_floor = None
    menu_third_floor = None

    week_number = datetime.datetime.today().isocalendar()[1]

    for post in data:
        time = post['created_time']
        message = post['message']

        week_match_third = re.match(pattern_third_floor, message, flags=re.IGNORECASE)
        week_match_first = re.match(pattern_first_floor, message, flags=re.IGNORECASE)
        if menu_third_floor is None and week_match_third is not None and int(week_match_third.group(1)) == week_number:
            match = re.search(pattern_days, message, flags=re.IGNORECASE | re.DOTALL)
            if match:
                menu_third_floor = match.group(1, 2, 3, 4, 5)
        elif menu_first_floor is None and week_match_first is not None and int(week_match_first.group(1)) == week_number:
            match = re.search(pattern_days, message, flags=re.IGNORECASE | re.DOTALL)
            if match:
                menu_first_floor = match.group(1, 2, 3, 4, 5)

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
