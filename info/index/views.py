from flask import session

from info.models import User
from . import index_blue
from flask import render_template,current_app


@index_blue.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('news/favicon.ico')


@index_blue.route('/')
def index():
    # 獲取用戶id
    User_id = session.get('user_id')
    # m默認值
    user = None
    if User_id:
        # 根據id查當前用戶
        user = User.query.get(User_id)
    data = {
        # 需要在頁面展示用戶的數據,所以需要把user對象裝換成字典
        'user_info':user.to_dict() if user else None
    }



    return render_template('news/index.html',data = data)