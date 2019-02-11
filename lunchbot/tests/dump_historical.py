#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

import re
import os
import io
from dateutil.parser import parse

from ..config import FACEBOOK_SECRET, FACEBOOK_ID
from ..apiwrappers import authenticated_graph, filter_messages
from ..main import (
    patterns_first_floor,
    patterns_third_floor,
    patterns_combined,
    floor_flags,
    combined_flags,
    patterns_daily_combined
)


here = os.path.abspath(os.path.dirname(__file__))


def is_menu_message(message, patterns, flags=None):
    if flags is None:
        flags = floor_flags
    for pattern in patterns:
        match = re.match(pattern, message, flags=flags)
        if match is not None:
            return True
    return False

def dump_menu(post, postfix):
    created_time = parse(post['created_time'])
    filename = created_time.strftime('%y%m%d') + '-%s.txt' % postfix
    path = os.path.join(here, 'historical', filename)
    if not os.path.exists(path):
        with io.open(path, mode='wt', encoding='utf-8') as f:
            f.write(post['message'])

graph = authenticated_graph(FACEBOOK_ID, FACEBOOK_SECRET)
pages = graph.get('technopolisitfornebu/posts', page=True)

for posts in pages:
    for post in filter_messages(posts):
        message = post['message']
        if is_menu_message(message, patterns_combined, combined_flags):
            dump_menu(post, 'combined')
        elif is_menu_message(message, patterns_first_floor):
            dump_menu(post, 'first')
        elif is_menu_message(message, patterns_third_floor):
            dump_menu(post, 'third')
        elif is_menu_message(message, patterns_daily_combined, combined_flags):
            dump_menu(post, 'dailycomb')
