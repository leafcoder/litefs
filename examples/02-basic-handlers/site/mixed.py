def handler(self):
    self.start_response(200)
    return [b'Hello', ' ', b'world', '!']
