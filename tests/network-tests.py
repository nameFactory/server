#!/usr/bin/env python3

import requests

url = 'https://api.namefactory.pl'

user_json = requests.post(url + '/user', json={}).json()
print(user_json)
username = user_json['username']
password = user_json['password']

ranking_json = requests.post(url + '/ranking', json={'username': username, 'password': password, 'is_male': 0, 'ranking_id': 1, 'tag_ids': [1]}).json()
print(ranking_json)

for i, j in [(1, 2), (3, 4), (5, 6), (101, 102), (103, 104), (105, 106)]:
    match_json = requests.post(url + '/match', json={'username': username, 'password': password, 'ranking_id': 1, 'winner_id': i, 'loser_id': j}).json()
print(match_json)

match_list = requests.post(url + '/match_list', json={'username': username, 'password': password, 'ranking_id': 1}).json()
print(match_list)
