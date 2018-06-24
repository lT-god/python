from flask import g
from flask import request, jsonify
from flask import session

from info.models import User, News, Category
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import index_blue
from flask import render_template,current_app


@index_blue.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('news/favicon.ico')


@index_blue.route('/')
@user_login_data
def index():
    user = g.user
    # # 獲取用戶id
    # User_id = session.get('user_id')
    # # m默認值
    # user = None
    # if User_id:
    #     # 根據id查當前用戶
    #     user = User.query.get(User_id)
    # 右边的热门新闻排序
    # 获取到热门新闻,通过点击时间进行倒叙排序,让后获取到前面10条新闻
    news_model = News.query.order_by(News.clicks.desc()).limit(10)

    news_dict = []

    for news in news_model:
        news_dict.append(news.to_dict())

    # 获取新闻分类数据
    categories = Category.query.all()

    # 定义列表保持分类数据
    categories_ditcs = []

    for category in categories:
        # 拼接内容
        categories_ditcs.append(category.to_dict())


    data = {
        # 需要在頁面展示用戶的數據,所以需要把user對象裝換成字典
        'user_info':user.to_dict() if user else None,
        'click_news_list':news_dict,
        'categories':categories_ditcs
    }

    return render_template('news/index.html', data=data)


@index_blue.route('/news_list')
def news_list():
    cid = request.args.get('cid','1')
    # 当前页面数据
    page = request.args.get('page','1')
    # 每个页面有多少条数据
    per_page = request.args.get('per_page','10')
    # 校验数据
    try:
        cid = int(cid)
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 查询数据并分页
    filters = [News.status == 0]
    # 如果分类id不为1,那么添加分类id的过滤

    if cid != 1:
        filters.append(News.category_id == cid )
    # 第三个参数表示没有错误输出
    paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page,per_page,False)

    # 每个页面上面需要展示的数据
    items = paginate.items
    # 当前页面
    current_page = paginate.page
    # 总页数
    total_page = paginate.pages

    news_list = []
    for news in items:
        news_list.append(news.to_dict())
    data = {
        # 表示当前页面需要展示的数据
        'news_dict_li':news_list,
        # 表示当前页面
        'current_page':current_page,
        # 一共有多少个页面
        'total_page':total_page,
        # 分类id
        'cid':cid
    }
    return jsonify(errno = RET.OK,errmsg = 'ok',data = data)





