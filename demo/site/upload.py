def handler(self):
    files = self.files
    for fobj in files.values():
        yield fobj.read()