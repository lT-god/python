import logging
import os
from logging.handlers import RotatingFileHandler
from flask import Flask
from config import Config,config_data,DevelopmentConfig,ProductionConfig
from flask_sqlalchemy import SQLAlchemy
import redis
from flask_session import Session
from flask_wtf.csrf import CSRFProtect, generate_csrf

''''
info.__init__:放整个项目模块里面的所有业务逻辑需要用到的一些值
項目基本配置
config類
SQLAlchemy 數據庫擴展
redis數據庫擴展
CSRF包含請求體的請求都需要開啓csrf
Session 利用flask擴展,將session數據保存到redis
flask_script 數據庫遷移擴展Manager
'''
# 設置日志記錄等級
logging.basicConfig(level=logging.DEBUG) # debug等級
# 創建日志記錄器,指明日志保存的路徑.每個日志文件的最大大小,保存的日志文件個數上限
file_log_handler = RotatingFileHandler('logs/log',maxBytes=1024*1024*100,backupCount=10)
# 創建日志記錄的格式 日志等級 輸入日志信息的文件名 行數 日志信息
formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
# 爲剛創建的日志記錄器設置日志記錄格式
file_log_handler.setFormatter(formatter)
# 爲全局的日志工具對象(flask app使用的)添加日志記錄器
logging.getLogger().addHandler(file_log_handler)


db = SQLAlchemy()
redis_store = None # type:redis.StrictRedis


def create_app(config_name):
    app = Flask(__name__)

    class_name = config_data.get(config_name)
    app.config.from_object(class_name)

    db.init_app(app)

    global redis_store
    redis_store = redis.StrictRedis(host=class_name.REDIS_HOST,port=class_name.REDIS_PORT,decode_responses= True)
    Session(app)
    CSRFProtect(app)

    @app.after_request
    def after_request(response):
        # 調用函數生成csrf_token
        csrf_token = generate_csrf()
        response.set_cookie('csrf_token',csrf_token)
        print(os.getcwd(),'test')
        return response




    # 導入user藍圖並且注冊
    from info.user import user_blue
    app.register_blueprint(user_blue)

    # 導入index藍圖擯棄注冊

    from info.index import index_blue
    app.register_blueprint(index_blue)

    # 導入index藍圖擯棄注冊

    from info.passport import passport_blue
    app.register_blueprint(passport_blue)

    return app