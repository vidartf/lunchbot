#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

import re
import os
import io
from dateutil.parser import parse

from ..config import FACEBOOK_SECRET, FACEBOOK_ID
from ..apiwrappers import authenticated_graph, filter_messages
from ..main import pattern_first_floor, pattern_third_floor, floor_flags


here = os.path.abspath(os.path.dirname(__file__))


def is_menu_message(message, pattern):
    match = re.match(pattern, message, flags=floor_flags)
    return match is not None

graph = authenticated_graph(FACEBOOK_ID, FACEBOOK_SECRET)
pages = graph.get('technopolisitfornebu/posts', page=True)

for posts in pages:
    for post in filter_messages(posts):
        message = post['message']
        is_first_floor_menu = is_menu_message(message, pattern_first_floor)
        is_third_floor_menu = is_menu_message(message, pattern_third_floor)
        if is_first_floor_menu or is_third_floor_menu:
            created_time = parse(post['created_time'])
            postfix = 'first' if is_first_floor_menu else 'third'
            filename = created_time.strftime('%y%m%d') + '-%s.txt' % postfix
            path = os.path.join(here, 'historical', filename)
            if not os.path.exists(path):
                with io.open(path, mode='wt', encoding='utf-8') as f:
                    f.write(message)
