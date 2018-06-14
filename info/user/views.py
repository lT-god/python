from . import user_blue


@user_blue.route('/user')
def user():
    return 'user'