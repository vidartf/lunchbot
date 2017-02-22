#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

import argparse
import configparser
import os


parser = argparse.ArgumentParser(
    description='A bot for slack that fetches and parses the lunch menu for Technopolis IT Fornebu'
)
parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")


here = os.path.abspath(os.path.dirname(__file__))
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
