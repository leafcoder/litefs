def handler(self):
    files = self.files
    yield '<pre>'
    for fobj in files.values():
        yield fobj.read()
    yield '</pre>'