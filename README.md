
1. 快速启动
==============

1.1 启动脚本
---------------

    import sys
    sys.dont_write_bytecode = True

    import litefs
    litefs = litefs.Litefs(
        address='0.0.0.0:8080', webroot='./site', debug=True
    )
    litefs.run(timeout=2.)

将上面的代码保存为 run.py 文件。

1.2 页面脚本
---------------

在网站目录（注：启动脚本中 webroot 的目录）中，添加一个后缀名为 **.py** 的文件，如 example.py，代码如下：

    def handler(self):
        self.start_response(200, headers=[])
        return 'Hello world!'

    or

    def handler(self):
        return 'Hello world!'

1.3 启动网站
-----------

    $ python run.py
    Server is running at 0.0.0.0:8080
    Hit Ctrl-C to quit.

运行启动脚本后，访问 http://0.0.0.0:8080/example，您会看到 `Hello world!`。
