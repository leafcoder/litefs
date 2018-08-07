#coding: utf-8

def handler(self):
    print self.environ
    user_agent = self.environ.get('HTTP_USER_AGENT')
    print user_agent
    return '你的浏览器是：%s' % user_agent
