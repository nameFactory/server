#!/usr/bin/env python3
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20))

    def __init__(self, username):
        self.username = username

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


@app.route('/')
def hello():
    return 'Hello.'


@app.route('/user')
def get_users():
    return jsonify([u.as_dict() for u in User.query.all()])


@app.route('/user/<int:user_id>')
def get_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    if user:
        return jsonify(user.as_dict())
    return jsonify({'errors': ['User not found']})


if __name__ == '__main__':
    app.run()
