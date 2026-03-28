def handler(self):
    self.start_response(200, [('Content-Type', 'text/html')])
    return {"message": "Hello, World!", "status": "success"}