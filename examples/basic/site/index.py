def handler(self):
    self.start_response(200, [('Content-Type', 'text/html')])
    return ['<h1>Hello World</h1>']