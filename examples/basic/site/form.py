def handler(self):
    print('POST', self.post)
    return [self.get, self.post, self.json, self.body]