def handler(self):
    self.start_response(200, [('Content-Type', 'application/json')])
    return {"message": "Hello, World!", "status": "success"}
