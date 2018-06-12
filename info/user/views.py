from . import index_blue


@index_blue.route('/')
def index():
    return 'index導入藍圖最後一邊'