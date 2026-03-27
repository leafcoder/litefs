def handler(self):
    def generate_content():
        for i in range(5):
            yield f'line {i}\n'.encode('utf-8')
    return generate_content()
