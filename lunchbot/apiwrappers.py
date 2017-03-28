#!/usr/bin/env python
# coding: utf-8

from facepy import GraphAPI

from slackclient import SlackClient


def get_facebook_token(id, secret):
    graph = GraphAPI()
    request = 'oauth/access_token?client_id=%s&client_secret=%s&grant_type=client_credentials'
    token = graph.get(request % (id, secret))
    if isinstance(token, dict):
        return token['access_token']
    elif isinstance(token, str):
        # Remove prefix:
        return token.replace('access_token=', '')
    else:
        raise ValueError(
            'Facebook GraphAPI token returned by Facebook of unknown type')


def authenticated_graph(id, secret):
    facebook_token = get_facebook_token(id, secret)
    return GraphAPI(facebook_token)


def filter_messages(posts):
    data = posts['data']
    for post in data:
        if 'message' in post:
            yield post


class SlackPoster:
    def __init__(self, token, channels):
        self.client = SlackClient(token)
        self.channels = channels

    def post(self, message):
        for ch in self.channels:
            self.client.api_call(
                'chat.postMessage',
                channel=ch,
                text=message,
                as_user=False,
                username='lunchbot',
                icon_emoji=':spaghetti:'
            )
