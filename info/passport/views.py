
import random

import re
from datetime import datetime

from flask import session

from info import constants, db
from info import redis_store
from info.libs.yuntongxun.sms import CCP
from info.models import User
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from . import passport_blue
from flask import request,jsonify,current_app,make_response
'''
index.views:
只放置登入注冊的業務邏輯
'''


# 生成圖片驗證碼
@passport_blue.route('/image_code')
def index():
    print(request.url)

    # 獲取前段提交過來的uuid
    code_id = request.args.get('code_id')
    print(code_id)

    if not code_id:
        return jsonify(
            ERRCODE = RET.PARAMERR,
            ERRMSG = "參數錯誤"
        )
        # 获取到图片验证码
        # name:表示图片验证码的名字
        # text:表示图片验证码里面的内容
        # image:这个是验证码的图片
    name, text, image = captcha.generate_captcha()
    print('圖片驗證碼='+text)
    # 获取到验证码之后,存储到redis数据库当中
    # 第一个参数表示name
    # 第二个参数表示验证码里面具体的内容
    # 第三个参数是redis的过期时间,单位是秒
    redis_store.set('sms_code_'+ code_id,text,constants.IMAGE_CODE_REDIS_EXPIRES)

    # 初始化一個響應體
    resp = make_response(image)
    return resp

# 短信驗證碼
@passport_blue.route('/smscode',methods=['POST'])
def sms_code():
    print("前端發來的地址:" + request.url)
    #  TODO 发送短信验证码
    #  var params = {
    #     "mobile": mobile,
    #     "image_code": imageCode,
    #     "image_code_id": imageCodeId
    # }
    # 獲取用戶在注冊頁面填寫的手機號
    mobile = request.json.get('mobile')
    # 獲取用戶在注冊頁面填寫的圖片驗證碼
    image_code =request.json.get('image_code')
    # 獲取和圖片綁定一起的code_id(也就是uuid)
    image_code_id = request.json.get('image_code_id')
    # 從redis服務器獲取到uuid
    redis_image_code = redis_store.get('sms_code_'+ image_code_id)

    if not redis_image_code:
        return jsonify(errno = RET.NODATA, errmsg= '圖片驗證碼過期')

        # 判断用户输入的验证码是否有问题
        # lower()提高用户体验,把用户输入的值和服务器的值全部小写
    if image_code.lower() != redis_image_code.lower():
        return jsonify(errno = RET.PARAMERR,errmsg = '驗證碼輸入錯誤')

    # 隨機生成驗證碼
    result = random.randint(0,999999)

    # 保持驗證碼是六位
    sms_code = '%06d'%result
    print('短信驗證碼=' + sms_code)
    # 存儲後端隨機生成的驗證碼
    redis_store.set('code' + mobile ,sms_code, 300)
    # 发送短信
    # 第一个参数发送给哪个手机号,最多一次只能发送200个手机号,通过,分割
    # 第二个参数是数组形式进行发送[sms_code,100],数组里面的第一个参数表示随机验证码,第二个参数表示多久过期,单位是分钟
    # 第三个参数表示模板id 默认值表示1
    # statusCode = CCP().send_template_sms(mobile,[sms_code,5],1)
    #
    # if statusCode != 0:
    #     return jsonify(errno = RET.THIRDERR,errmsg = "發送短信失敗")

    return  jsonify(errno = RET.OK,errmsg = '發送短信成功')


@passport_blue.route('/register',methods = ['POST'])
def register():
    # 用戶輸入的手機號碼
    mobile = request.json.get('mobile')
    # 用戶輸入的手機驗證碼
    smscode = request.json.get('smscode')
    # 用戶輸入的密碼
    password = request.json.get("password")

    if not re.match(r'1[345678]\d{9}',mobile):
        return jsonify(errno = RET.PARAMERR,errmsg='手機號碼輸入錯誤')

    # 檢驗手機驗證碼
    # 從redis裏面獲取數據裏面緩存的手機驗證碼
    redis_sms_code = redis_store.get('code' + mobile)
    if redis_sms_code != smscode:
        return jsonify(error = RET.PARAMERR,errmsg='驗證碼輸入錯誤')

    user = User()
    user.mobile = mobile
    user.nick_name = mobile
    user.password = password
    # datetime.now() 獲取當前的時間,存儲到數據庫
    user.last_login = datetime.now()
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()

    # 把用戶注冊的信息設置給session
    session['mobile'] = user.mobile
    session['user_id'] = user.id
    session['nick_name'] = user.mobile

    return jsonify(errno = RET.OK,errmsg='注冊成功')

'''
登入
'''
@passport_blue.route('/login',methods = ['POST'])
def login():
    mobile = request.json.get('mobile')
    password = request.json.get('password')
    user = User.query.filter(User.mobile == mobile).first()
    if not user:
        return jsonify(errno = RET.NODATA,errmsg='請注冊')
    # 檢查代碼是否正確
    if not user.check_password(password):
        return jsonify(errno = RET.PARAMERR,errmsg='請輸入正確的密碼')

    # 把用戶注冊的數據設置給session

    session['mobile'] =user.mobile
    session['user_id'] = user.id
    session['nick_name'] = user.mobile

    user.last_login = datetime.now()
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
    return jsonify(errno=RET.OK,errmsg = '登入成功')

'''
退出
'''
@passport_blue.route('/logout')
def logout():
    # 退出,清空session裏面的數據
    session.pop('mobile',None)
    session.pop('user_id',None)
    session.pop('nick_name',None)
    return jsonify(errno=RET.OK,errmsg = '退出成功')

















