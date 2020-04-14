def handler(self):
    for key in dir(self):
        print(key, getattr(self, key))
    return 'Hello world!'