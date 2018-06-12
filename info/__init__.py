from flask import Flask
from config import Config,config_data,DevelopmentConfig,ProductionConfig
from flask_sqlalchemy import SQLAlchemy
import redis
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
''''
項目基本配置
config類
SQLAlchemy 數據庫擴展
redis數據庫擴展
CSRF包含請求體的請求都需要開啓csrf
Session 利用flask擴展,將session數據保存到redis
flask_script 數據庫遷移擴展Manager

'''
db = SQLAlchemy()
redis_store = None


def create_app(config_name):
    app = Flask(__name__)

    db.init_app(app)

    class_name = config_data.get(config_name)
    app.config.from_object(class_name)

    global redis_store
    redis_store = redis.StrictRedis(host=class_name.REDIS_HOST,port=class_name.REDIS_PORT)
    CSRFProtect(app)
    Session(app)

    # 導入藍圖並且注冊
    from info.user import index_blue
    app.register_blueprint(index_blue)

    return app