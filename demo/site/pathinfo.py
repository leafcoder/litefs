def handler(self):
    print self.environ
    print self.path_info
    return 'ok'