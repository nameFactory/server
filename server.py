#!/usr/bin/env python3
from hashlib import sha256
from uuid import uuid4

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

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
        self.password = sha256(plaintext_password.encode()).hexdigest()
        self.email = email


class Ranking(db.Model, ModelMixins):
    id = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __init__(self, id_user):
        self.id_user = id_user


@app.route('/')
def hello():
    return 'Hello.'


@app.route('/user', methods=['POST'])
def new_user():
    username = str(uuid4())
    password = str(uuid4())
    email = request.get_json().get('email')
    user = User(username, password, email)
    db.session.add(user)
    db.session.commit()
    result = user.as_dict(blacklist=['id'])
    result['password'] = password  # on creation, return password in plain text
    return jsonify(result)


if __name__ == '__main__':
    app.run()
