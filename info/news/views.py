from flask import abort
from flask import current_app
from flask import g, jsonify
from flask import render_template
from flask import request

from info import db
from info.models import News, Comment, CommentLike, User
from info.utils.response_code import RET
from . import news_blue
from info.utils.common import user_login_data


@news_blue.route("/<int:news_id>")
@user_login_data
def news_detail(news_id):
    # g对象可以理解成一个盒子,或者一个容器
    user = g.user

    # if not user:
    #     return jsonify(errno=RET.SESSIONERR,errmsg='没有登入')

    """
    右边的热门新闻排序
    获取到热门新闻,通过点击时间进行倒叙排序,让后获取到前面10条新闻
    """

    news_model_list = News.query.order_by(News.clicks.desc()).limit(10)

    news_dict = []

    for news in news_model_list:
        news_dict.append(news.to_dict())

    """
    展示详情页面
    """
    # 展示详情页面的新闻
    # 根据前端传过来的新闻id创建该新闻的实例对象,进行字段操作
    news = News.query.get(news_id)

    if not news:
        # 返回数据未找到页面
        abort(404)

    # 点击完成之后,新闻+1 ,目的是实现右边的热门新闻
        news.clicks += 1

    """
    新闻收藏栏目
    """

    # 判断是否收藏该新闻,默认值为false
    is_collected = False
    # 判断用户是否收藏过该新闻
    if user:
        if news in user.collection_news:
            is_collected = True

    '''查询当前新闻的所有评论'''

    comment_list = Comment.query.filter(Comment.news_id==news_id).order_by(Comment.create_time.desc()).all()

    """获取到用户所有评论点赞的数据"""
    comment_likes = []
    comment_like_ids = []
    if user:
        # 查询用户点赞了那些评论
        comment_likes = CommentLike.query.filter(CommentLike.user_id == user.id).all()
        # 取出来所有点赞的id
        comment_like_ids = [comment_like.comment_id for comment_like in comment_likes]

    comment_dict_list = []
    for item in comment_list:
        comment_dict = item.to_dict()
        # 默认情况下,所有的评论是没有被点赞的,所有设置为false
        comment_dict['is_like'] = False
        # 判断用户是否点赞该评论
        if item.id in comment_like_ids:
            comment_dict['is_like'] = True

        comment_dict_list.append(comment_dict)
    # 这个参数表示我关注了谁,如果没有关注显示为false,第一次进来默认是没有关注的,所以为false
    is_followed = False
    # new.user 获取到当前新闻的作者
    # 如果当前新闻有作者,并且用户已经登陆了,才能进行关注
    if news.user and user:
        print('user.followed=',user.followed)
        if news.user in user.followed:
            is_followed = True

    print('is_followed=',is_followed)
    data = {
        'user_info': user.to_dict() if user else None,
        'click_news_list': news_dict,
        'news': news.to_dict(),
        'is_collected':is_collected,
        'comments':comment_dict_list,
        'is_followed': is_followed
    }

    return render_template('news/detail.html', data=data)


@news_blue.route('/news_collect', methods=['POST'])
@user_login_data
def news_collect():
    """新闻收藏"""
    user = g.user
    news_id = request.json.get('news_id')
    action = request.json.get('action')
    # 检查是否有用户
    if not user:
        return jsonify(errno=RET.SESSIONERR,errmsg='用户未登录')
    # 检查是否有新闻id
    if not news_id:
        return jsonify(errno=RET.PARAMERR,errmsg='参数错误')
    # 检查action参数是否规范
    if action not in ('collect','cancel_collect'):
        return jsonify(errno=RET.PARAMERR,errmsg='参数错误')
    # 检查有新闻id之后是否能查询到数据库数据
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='查询数据失败')

    # 检查有新闻id之后是否能查询到数据库数据,查询数据库数据为空
    if not news:
        return jsonify(errno=RET.NODATA,errmsg='新闻数据不存在')
    # 检查数据正常,判断前端传过来的操作数据action值是否收藏
    # 如果传过来数据是收藏,则添加新闻数据到收到列表
    if action =='collect':
        user.collection_news.append(news)
    else:
        # 如果传过来数据是取消收藏,则删除新闻数据到收到列表
        user.collection_news.remove(news)
    # 将数据进行提及执行,涉及数据操作使用try提交

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 操作失败,回滚操作
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg='保存失败')
    return jsonify(errno=RET.OK,errmsg='操作成功')

@news_blue.route('/news_comment',methods=['POST'])
@user_login_data
def news_comment():
    '''添加评论'''
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR,errmsg='用户未登录')
    # 获取前端参数
    news_id = request.json.get('news_id')
    comment_str = request.json.get('comment')
    parent_id = request.json.get('parent_id')

    if not all([news_id,comment_str]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数不足')

    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="该新闻不存在")

    # 初始化模型，保存数据
    comment = Comment()
    comment.user_id = user.id
    comment.news_id = news_id
    comment.content = comment_str

    if parent_id:
        comment.parent_id = parent_id

    # 保存用户id,新闻id,新闻内容,当前端有父类的评论id传到后台时,也保存
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='保存评论数据失败')

    return jsonify(errno=RET.OK,errmsh='评论成功',data=comment.to_dict())


@news_blue.route('/comment_like',methods=["POST"])
@user_login_data
def set_comment_like():
    '''评论点赞功能'''
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 获取参数

    comment_id = request.json.get('comment_id')
    news_id = request.json.get('news_id')
    action = request.json.get('action')

    # 判断参数

    if not all([comment_id,news_id,action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in ('add','remove'):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 查询评论数据
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e :
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

    if not comment:
        return jsonify(errno=RET.NODATA, errmsg="评论数据不存在")

    if action == 'add':
        comment_like = CommentLike.query.filter_by(comment_id=comment_id,user_id=user.id).first()
        if not comment_like:
            comment_like = CommentLike()
            comment_like.comment_id = comment_id
            comment_like.user_id = user.id
            db.session.add(comment_like)
            # 增加点赞条数
            comment.like_count += 1

    else:
        # 删除点赞数据
        comment_like = CommentLike.query.filter_by(comment_id=comment_id,user_id=user.id).first()
        if comment_like:
            db.session.delete(comment_like)
            comment.like_count -=1


    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="操作失败")

    return jsonify(errno=RET.OK, errmsg="操作成功")

'''关注与取消关注'''


@news_blue.route('/followed_user', methods=['POST'])
@user_login_data
def followed_user():
    print('user/follwed_user:')
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR,errmsg='请先登陆')

    # user_id表示我关注的那个用户的id
    user_id = request.json.get('user_id')
    # 根据前端传来的user_id创建实例对象进行数据库字段操作
    other= User.query.get(user_id)
    # 关注或是取消关注字段
    action = request.json.get('action')

    if action == 'follow':
        # 如果当前在登陆用户的关注人列表没有other对象,那就关注
        if other not in user.followed:
            user.followed.append(other)
            print('other',other)

    else:
        if other in user.followed:
            user.followed.remove(other)

    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="取消关注成功")









