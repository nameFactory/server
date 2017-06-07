#!/usr/bin/env python3
from hashlib import sha256
import json
import random
from uuid import uuid4

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import numpy as np
from numpy.random import choice

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class ModelMixins:
    def as_dict(self, blacklist=[]):
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
            if c.name not in blacklist
        }


class User(db.Model, ModelMixins):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32))
    password = db.Column(db.String(64))
    email = db.Column(db.String(64))

    def __init__(self, username, plaintext_password, email=None):
        self.username = username
        self.password = plaintext_to_hash(plaintext_password)
        self.email = email


class Ranking(db.Model, ModelMixins):
    id = db.Column(db.Integer, primary_key=True)
    id_user_creator = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_male = db.Column(db.Boolean)

    def __init__(self, id_user_creator, is_male):
        self.id_user_creator = id_user_creator
        self.is_male = is_male


class Tag(db.Model, ModelMixins):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))

    def __init__(self, name):
        self.name = name


class Ranking2Tag(db.Model, ModelMixins):
    id_ranking = db.Column(
        db.Integer, db.ForeignKey('ranking.id'), primary_key=True
    )
    id_tag = db.Column(
        db.Integer, db.ForeignKey('tag.id'), primary_key=True
    )

    def __init__(self, id_ranking, id_tag):
        self.id_ranking = id_ranking
        self.id_tag = id_tag


class User2Ranking(db.Model, ModelMixins):
    id_user = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    id_ranking = db.Column(
        db.Integer, db.ForeignKey('ranking.id'), primary_key=True
    )
    ref_id = db.Column(db.Integer, primary_key=True)

    def __init__(self, id_user, id_ranking, ref_id):
        self.id_user = id_user
        self.id_ranking = id_ranking
        self.ref_id = ref_id


name2tag = db.Table(
    'name2tag',
    db.Column('id_name', db.Integer, db.ForeignKey('name.id')),
    db.Column('id_tag', db.Integer, db.ForeignKey('tag.id'))
)


class Name(db.Model, ModelMixins):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    description = db.Column(db.Text())
    is_male = db.Column(db.Boolean)
    tags = db.relationship('Tag', secondary=name2tag)

    def __init__(self, name, is_male, description=''):
        self.name = name
        self.is_male = is_male
        self.description = description

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_male': self.is_male,
            'tags': [tag.id for tag in self.tags]
        }


class Match(db.Model, ModelMixins):
    id = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('user.id'))
    id_ranking = db.Column(db.Integer, db.ForeignKey('ranking.id'))
    id_winner = db.Column(db.Integer, db.ForeignKey('name.id'))
    id_loser = db.Column(db.Integer, db.ForeignKey('name.id'))

    def __init__(self, id_user, id_ranking, id_winner, id_loser):
        self.id_user = id_user
        self.id_ranking = id_ranking
        self.id_winner = id_winner
        self.id_loser = id_loser


def get_name_to_desc():
    def decode(s):
        return bytes(s, 'ascii').decode('unicode-escape')

    with open('desc.json', 'r') as f:
        raw = ''.join(f.readlines())
        return {decode(k): decode(v) for k, v in json.loads(raw).items()}


def populate_db_with_names():
    polish = Tag('polish')
    db.session.add(polish)
    db.session.flush()
    filetags = [
        # (file, [tag1, tag2, ...], is_male)
        ('data/pl_male.txt', [polish], True),
        ('data/pl_female.txt', [polish], False)
    ]
    name2desc = get_name_to_desc()
    for ft in filetags:
        with open(ft[0], 'r') as f:
            for n in f:
                name = Name(n.strip(), ft[2], name2desc.get(n.strip(), ''))
                db.session.add(name)
                db.session.flush([name])
                for tag in ft[1]:
                    name.tags.append(tag)
    db.session.commit()


def plaintext_to_hash(s):
    return sha256(s.encode()).hexdigest()


def error(msg):
    return jsonify({'errors': [msg]})


@app.route('/')
def hello():
    return 'Hello.'


@app.route('/user', methods=['POST'])
def new_user():
    username = str(uuid4())
    password = str(uuid4())
    email = request.get_json().get('email') or ''
    user = User(username, password, email)
    db.session.add(user)
    db.session.commit()
    result = user.as_dict(blacklist=['id'])
    result['password'] = password  # on creation, return password in plain text
    return jsonify(result)


@app.route('/ranking', methods=['POST'])
def new_ranking():
    data = request.get_json()
    try:
        username = data['username']
        password = plaintext_to_hash(data['password'])
        ref_id = data['ranking_id']
        is_male = int(data['is_male'])
        tags = data.get('tag_ids', [])
    except KeyError:
        return error(
            'You have to provide username, password, ranking_id, is_male '
            'and tag_ids'
        )
    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return error('Invalid username/password')
    ranking = Ranking(user.id, is_male)
    db.session.add(ranking)
    db.session.flush()
    for tag in tags:
        db.session.add(Ranking2Tag(ranking.id, tag))
    db.session.add(User2Ranking(user.id, ranking.id, ref_id))
    db.session.commit()
    return jsonify({})


@app.route('/match', methods=['POST'])
def add_match():
    data = request.get_json()
    try:
        username = data['username']
        password = plaintext_to_hash(data['password'])
        ref_id = data['ranking_id']
        winner_id = data['winner_id']
        loser_id = data['loser_id']
    except KeyError:
        return error(
            'You have to provide username, password, ranking_id, winner_id '
            'and loser_id'
        )
    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return error('Invalid username/password')
    ranking_id = User2Ranking.query.filter_by(
        id_user=user.id, ref_id=ref_id
    ).one().id_ranking
    ranking = Ranking.query.filter_by(id=ranking_id).one()
    match = Match(user.id, ranking.id, winner_id, loser_id)
    db.session.add(match)
    db.session.commit()
    return jsonify({})


@app.route('/names_db')
def get_names_db():
    tags = Tag.query.all()
    names = Name.query.all()
    return jsonify(
        {
            'tags': [tag.as_dict() for tag in tags],
            'names': [name.as_dict() for name in names]
        }
    )


@app.route('/match_list', methods=['POST'])
def get_matches():
    data = request.get_json()
    try:
        username = data['username']
        password = plaintext_to_hash(data['password'])
        ref_id = data['ranking_id']
    except KeyError:
        return error('You have to provide username, password and ranking_id')
    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return error('Invalid username/password')
    ranking_id = User2Ranking.query.filter_by(
        id_user=user.id, ref_id=ref_id
    ).one().id_ranking
    is_male = int(Ranking.query.filter_by(id=ranking_id).one().is_male)
    raw = db.engine.execute('select id from name where is_male = ?', is_male)

    name2score = {
        x[0]: 0
        for x in raw
    }
    name2usage = {
        x[0]: False
        for x in raw
    }
    matches = db.engine.execute(
        'select id_winner, id_loser from match where id_user = ?', user.id
    )
    for m in matches:
        if m[0] not in name2score or m[1] not in name2score:
            continue
        name2score[m[0]] += 1
        name2score[m[1]] -= 1
        for x in (m[0], m[1]):
            name2usage[x] = True
    not_used = [k for k, v in name2usage.items() if not v]
    used = [k for k, v in name2usage.items() if v]

    result = list()
    for _ in range(25):
        if len(not_used) > 2:
            n1, n2 = random.sample(not_used, 2)
        else:
            p = np.array(list(name2score.values()))
            p = np.arctan(p) + 1.7
            p = p/np.sum(p)
            n1, n2 = choice(
                list(name2score.keys()), size=2, replace=False, p=p
            )
            n1, n2 = random.sample(used, 2)
        result.append({'name_id1': n1, 'name_id2': n2})
    return jsonify({'result': result})


def _elo_rank(names):
    def get_expected_score(a, b):
        return 1 / (1 + 10**((b-a)/400))
    name2score = dict()
    for id_winner, id_loser in names:
        name2score[id_winner] = 1200
        name2score[id_loser] = 1200
    K = 64
    for id_winner, id_loser in names:
        winner_score = name2score[id_winner]
        loser_score = name2score[id_loser]
        winner_expected_score = get_expected_score(winner_score, loser_score)
        loser_expected_score = get_expected_score(loser_score, winner_score)
        name2score[id_winner] += K * (1 - winner_expected_score)
        name2score[id_loser] += K * loser_expected_score
    return [
        k for k, v in
        sorted(
            ((k, v) for k, v in name2score.items()),
            key=lambda x: x[1],
            reverse=True
        )
    ]


@app.route('/top50')
def get_top50():
    result = list()
    sql_template = (
        'select id_winner, id_loser from match m '
        'join name n on m.id_winner = n.id where n.is_male = {}'
    )
    for is_male in (False, True):
        sql = sql_template.format(int(is_male))
        r = db.engine.execute(sql)
        result.append(
            {
                'is_male': is_male,
                'top50': _elo_rank(r)[:50],
            }
        )
    return jsonify({'result': result})


if __name__ == '__main__':
    app.run()
