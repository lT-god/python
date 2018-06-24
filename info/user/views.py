from flask import abort
from flask import current_app
from flask import g, jsonify
from flask import redirect,url_for
from flask import request
from flask import session

from info import constants
from info import db
from info.models import Category, News, User
from info.utils.response_code import RET
from . import profile_blue
from flask import render_template
from info.utils.common import user_login_data
from info.utils.image_storage import storage

"""新闻列表"""
@profile_blue.route('/news_list')
@user_login_data
def news_list():
    page = request.args.get('p', 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    user = g.user
    paginate = News.query.filter(News.user_id == user.id).paginate(page,5,False)

    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    news_list = []

    for item in items:
        news_list.append(item.to_review_dict())

    data = {
        'current_page':current_page,
        'total_page':total_page,
        'news_list':news_list
    }

    return render_template('news/user_news_list.html',data=data)

"""新闻编辑发布"""


@profile_blue.route('/news_release',methods=['GET','POST'])
@user_login_data
def news_release():
    if request.method == 'GET':
        # 首先获取到新闻分类,然后传递到模板页码,进行展示
        category_list = Category.query.all()
        categorys = []
        for category in category_list:
            categorys.append(category.to_dict())
        categorys.pop(0)

        data = {
            "categories":categorys
        }
        return render_template('news/user_news_release.html',data=data)

    # 获取到表单页面提交过来的数据,获取的是用户发布的新闻数据
    title = request.form.get('title')
    category_id = request.form.get('category_id')
    digest = request.form.get('digest')
    index_image = request.files.get('index_image')
    content = request.form.get('content')

    if not all([title, category_id, digest, index_image, content]):
        return jsonify(errno = RET.PARAMERR,errmsg='参数错误')
    print("上传图片中")
    user = g.user
    # 尝试读取图片
    index_image = index_image.read()
    #  将标题图片上传到七牛
    key = storage(index_image)
    # 用户发布完成之后,我们需要把当前发布的新闻存储到数据库
    news = News()
    news.title = title
    news.source = '个人来源'
    news.digest = digest
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.category_id = category_id
    news.user_id = user.id

    # 当前状态一表示正在审核中
    news.status = 1
    db.session.add(news)
    db.session.commit()

    return jsonify(errno=RET.OK,errmsg='发布成功')


@profile_blue.route('/collection')
@user_login_data
def collection():
    """新闻收藏列表"""
    # 当前表示用户所有收藏的新闻,获取所有新闻涉及分页,那么肯定是从第一页开始
    page = request.args.get('p',1)

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    user = g.user
    # 获取当前登陆用户的所有的收藏新闻列表
    # 第一个参数表示当前页面书
    # 第二参数表示当前每个页面一共有多少条数据

    paginate = user.collection_news.paginate(page,10,False)
    # item 每个页面的所有信息
    items = paginate.items

    # 当前页码
    current_page = paginate.page

    # 总的页码
    total_page = paginate.pages

    collections = []
    for item in items:
        collections.append(item.to_dict())

    data = {
        'collections':collections,
        'current_page':current_page,
        'total_page':total_page
    }
    return render_template('news/user_collection.html',data=data)


@profile_blue.route("/pass_info",methods=['GET', 'POST'])
@user_login_data
def pass_info():
    '''密码修改'''
    if request.method == 'GET':
        return render_template('news/user_pass_info.html')

    user = g.user
    # 获取新旧密码
    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")
    print("old_password=%s,new_password=%s" %(old_password, new_password))
    # 判断是否全都有值
    if not all([old_password,new_password]):
        return jsonify(errno=RET.PARAMERR,errmsg='请输入密码')
    # 判断就的密码是否正确,旧密码正确之后才能修改新密码
    if not user.check_password(old_password):
        return jsonify(errno=RET.PARAMERR,errmsg='旧密码错误')
    # 旧密码正确,就将获取到的新密码跟新到数据库
    user.password = new_password
    db.session.commit()
    return jsonify(errno=RET.OK,errmsg='修改密码成功')

@profile_blue.route('/user_follow')
@user_login_data
def user_follow():
    p = request.args.get('p',1)

    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p =1

    current_page = 1
    total_page = 1

    user = g.user
    # 获取用户关注的所有作者,并且将结果分类
    paginate = user.followed.paginate(p,10,False)

    # 获取当前页数据
    items = paginate.items

    # 获取当前页
    current_page = paginate.page

    # 获取总页数
    total_page = paginate.pages

    user_dict_li = []
    for follow_user in items:
        user_dict_li.append(follow_user.to_dict())

    data = {
        'users':user_dict_li,
        'total_page':total_page,
        'current_page':current_page
    }

    return render_template('news/user_follow.html',data=data)


@profile_blue.route("/other_info")
@user_login_data
def other_info():

    """查看其他用户信息"""

    user = g.user
    # 获取其他用户id
    user_id = request.args.get('id')
    if not user_id:
        abort(404)

    # 查询用户模型
    other = None
    try:
        other = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)

    if not other:
        abort(404)

    # 判断当前登陆用户是否关注过该用户
    is_followed = False
    if g.user:
        if other.followers.filter(User.id == user.id).count() > 0:
            is_followed = True

    data = {
        'user_info':user.to_dict(),
        'other_info':other.to_dict(),
        'is_followed':is_followed
    }

    return render_template('news/other.html',data=data)



@profile_blue.route('/other_news_list')
def other_news_list():
    p = request.args.get('p', 1)
    user_id = request.args.get("user_id")
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1
    if not all([p, user_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    user = User.query.get(user_id)
    if not user:
        return jsonify(errno=RET.NODATA, errmsg="用户不存在")


    current_page = 1
    total_page = 1

    # 获取用户关注的所有作者,并且将结果分类
    paginate = News.query.filter(News.user_id == user.id).paginate(p, 10, False)

    # 获取当前页数据
    items = paginate.items

    # 获取当前页
    current_page = paginate.page

    # 获取总页数
    total_page = paginate.pages

    news_dict_li = []
    for follow_user in items:
        news_dict_li.append(follow_user.to_dict())

    data = {
        'news_list': news_dict_li,
        'total_page': total_page,
        'current_page': current_page
    }

    return jsonify(errno=RET.OK, errmsg="OK", data=data)















"""用户图像上传修改"""


@profile_blue.route('/pic_info',methods=['GET','POST'])
@user_login_data
def pic_info():
    user = g.user
    if request.method == 'GET':
        data = {
            'user_info': user.to_dict() if user else None,
        }
        return render_template('news/user_pic_info.html',data=data)
    avatar = request.files.get('avatar').read()
    #  如果上传成功,那么就会返回一个url地址,或是叫key的值
    # 如果想在浏览器中流量刚刚上传的图片,那么必须通过骑牛的地址+刚刚返回的url,http: // oyucyko3w.bkt.clouddn.com / + url

    url = storage(avatar)
    user.avatar_url = url
    db.session.commit()
    return jsonify(error=RET.OK,errmsg='上传成功',data={'avatar_url': constants.QINIU_DOMIN_PREFIX + url})


"""签名/昵称/性别 基本信息修改"""
@profile_blue.route('/base_info',methods=['POST','GET'])
@user_login_data
def base_info():
    user = g.user
    if request.method == "GET":
        data = {
            'user_info': user.to_dict() if user else None,
        }
        return render_template('news/user_base_info.html',data=data)
    # 获取前端页面更新提交的数据
    nick_name = request.json.get('nick_name')
    signature = request.json.get('signature')
    gender = request.json.get('gender')

    # 将数据跟新到数据库
    user.nick_name = nick_name
    user.signature  = signature
    user.gender = gender
    # 跟新数据不用db.session.add(user)
    db.session.commit()
    # db.session.commit()是跟新mysql,session里面的数据是reids数据库
    session['nick_name']=user.nick_name
    session['gender'] = user.gender

    return jsonify(errno=RET.OK,errmsg='修改成功')


@profile_blue.route('/info')
@user_login_data
def info():
    user = g.user
    if not user:
        return redirect('/')

    data = {
        'user_info': user.to_dict() if user else None,
    }
    return render_template('news/user.html',data=data)

