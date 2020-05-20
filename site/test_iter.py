#-*- coding: utf-8 -*-

def handler(self):
    self.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return iter_response(self)

def iter_response(self):
    yield '<h1>Environ</h1>'
    for k, v in self.environ.items():
        yield '{}: {}'.format(k, v)
        yield '<br>'
    yield '<h1>Form</h1>'
    yield 'Params', str(self.params)
    yield 'data', str(self.data)
    yield '<br>'

    yield '<h1>Files</h1>'
    files = self.files
    for fp in files.values():
        yield '<div><textarea style="width: 100%" rows=10>'
        yield fp.read()
        yield '</textarea></div>'
        yield '<br>'
