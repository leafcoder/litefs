def handler(self):
    self.start_response(200)
    return ['hello'.encode('utf-8'), b' ', b'world']