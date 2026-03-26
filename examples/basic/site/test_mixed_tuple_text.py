from datetime import datetime

def handler(self):
    self.start_response(200, [('Content-Type', 'text/plain; charset=utf-8')])
    return (datetime.now(), True, 1, 'a')
