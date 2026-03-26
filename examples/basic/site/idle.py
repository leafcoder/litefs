import time
from greenlet import greenlet, getcurrent

def handler(self):
    asleep()
    self.start_response(200)
    return ['Hello World']


def asleep(seconds=0.01):
    idle(seconds)


def idle(seconds):
    from litefs.server.http_server import epoll
    curr = getcurrent()
    ts = time.time() + seconds
    epoll._idles.append((ts, curr))
    epoll._idles.sort()
    curr.parent.switch()