#!/usr/bin/env python
# coding: utf-8


from datetime import datetime
import logging

import requests
from bs4 import BeautifulSoup
from facepy import GraphAPI
from pytz import timezone
from slack import WebClient


logger = logging.getLogger("lunchbot")


def get_facebook_token(id, secret):
    graph = GraphAPI()
    request = (
        'oauth/access_token?client_id=%s&client_secret=%s&grant_type=client_credentials'
    )
    token = graph.get(request % (id, secret))
    if isinstance(token, dict):
        return token['access_token']
    elif isinstance(token, str):
        # Remove prefix:
        return token.replace('access_token=', '')
    else:
        raise ValueError('Facebook GraphAPI token returned by Facebook of unknown type')


def authenticated_graph(id, secret):
    facebook_token = get_facebook_token(id, secret)
    return GraphAPI(facebook_token)


def filter_messages(posts):
    for post in posts:
        if 'message' in post:
            yield post


class SlackPoster:
    def __init__(self, token, channels):
        self.client = WebClient(token)
        self.channels = channels

    def post(self, message):
        logger.info("Posting %r to %s", message, self.channels)
        for ch in self.channels:
            self.client.chat_postMessage(
                channel=ch,
                text=message,
                as_user=False,
                username='lunchbot',
                icon_emoji=':spaghetti:',
            )


## For scraping the facebook website


def extract_post_text(elem):
    """extract a post text from an html element"""
    chunks = []
    for e in elem.descendants:
        if isinstance(e, str):
            chunks.append(e.strip() + ' ')
        elif e.name.lower() in {'br', 'p'}:
            chunks.append('\n')
    return ''.join(chunks).strip()


def parse_post(content_wrapper):
    """Parse a post element on the page

    Returns a dict that looks enough like the post object from the API
    to be a drop-in replacement
    """
    timestamp = int(
        content_wrapper.find(class_="timestampContent").parent.attrs['data-utime']
    )
    dt = datetime.fromtimestamp(timestamp).astimezone(timezone("UTC"))

    content = content_wrapper.find(class_="userContent")
    for item in content.find_all(class_="text_exposed_hide"):
        item.decompose()
    return {"created_time": dt.isoformat(), "message": extract_post_text(content)}


def scrape_posts(page):
    r = requests.get('https://facebook.com/{}/posts'.format(page))
    r.raise_for_status()
    html = BeautifulSoup(r.text, features="html.parser")
    wrappers = html.find_all(class_='userContentWrapper')
    if not wrappers:
        raise ValueError("Couldn't find posts. Did Facebook HTML change?")

    return [parse_post(wrapper) for wrapper in wrappers]
