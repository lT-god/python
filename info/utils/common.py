from flask import g
from flask import session
import functools
from info.models import User


def do_index_class(index):
    """
    Custom filter, filter click sort
    :param index:
    :return:
    """
    if index == 0:
        return 'first'
    elif index ==1:
        return 'second'
    elif index == 2:
        return 'third'
    else:
        return ''


def user_login_data(f):
    @functools.wraps(f)
    def wrapper(*args,**kwargs):
        # 获取用户id
        user_id = session.get('user_id')
        # 设置默认user为none
        user = None
        if user_id:
            user = User.query.get(user_id)
        g.user = user
        return f(*args,**kwargs)
    return wrapper






# def user_login_data():
#     """
#     右上角判断用户是否登入
#     :return:
#     """
#     # 获取用户id
#     user_id = session.get('user_id')
#     # 设置默认user为none
#     user=None
#     if  user_id:
#        user = User.query.get(user_id)
#
#     return user