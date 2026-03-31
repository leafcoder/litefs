def handler(self):
    print(self.session_id,self.session.get('name'))
    self.session['name'] = 'Tomy2'
    # 手动保存 Session 数据
    self.session.save()
    return 'get put name'