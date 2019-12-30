#-*- coding: utf-8 -*-

def handler(self):
    yield '<h1>Environ</h1>'
    for k, v in self.environ.items():
        yield '{}: {}'.format(k, v)
        yield '<br>'

    yield '<h1>Form</h1>'
    yield self.form
    yield '<br>'

    yield '<h1>Files</h1>'
    files = self.files
    for fp in files.values():
        print(dir(fp))
        yield '<div><textarea style="width: 100%" rows=10>'
        yield fp.read()
        yield '</textarea></div>'
        yield '<br>'
