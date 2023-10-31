import os
import json
from bson.objectid import ObjectId
from pymongo import MongoClient
from flask import Flask
from flask_session import Session
import redis


def connect_db():
    # Thiết lập kết nối đến MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['ql_sach']
    return db


def create_app():

    # Chuyển ObjectId về dạng chuỗi
    class MyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, ObjectId):
                return str(obj)
            return super(MyEncoder, self).default(obj)

    app = Flask(__name__, static_folder='static')
    app.debug = True
    app.json_encoder = MyEncoder
    app.secret_key = 'y7JE9yRsb'

    from .view import view
    from .auth import auth
    app.register_blueprint(view, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    # Config Session
    # Lấy URL kết nối Redis từ biến môi trường hoặc sử dụng mặc định
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'y789JE9yRsb#'  # Tuỳ chọn
    app.config['SESSION_REDIS'] = redis.from_url(redis_url)
    Session(app)

    return app
