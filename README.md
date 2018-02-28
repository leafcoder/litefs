
# 1. 快速启动

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


# 2. CGI 规则

2.1 httpfile 对象是服务器上下文接口，接口如下：
--------------------------------------

接口类型 | 接口使用 | 接口描述
---- | --- | ----
环境变量（只读） | httpfile.environ | 环境变量
某环境变量 | httpfile.environ`[`_*envname*_`]` | 获取某环境变量
Session | httpfile.session | session 对象，可临时保存或获取内存数据
Session ID | httpfile.session_id | session 对象 ID，将通过 SET_COOKIE 环境变量返回给客户端浏览器
Form | httpfile.form | form 为字典对象，保存您提交到服务器的数据
Config | httpfile.config | 服务器的配置对象，可获取初始化服务器的配置信息
files | httpfile.files | 字典对象，保存上传的文件，格式为：{ *filename1*: *\<StringIO object\>*, *filename2*: *\<StringIO object\>* }
cookie | httpfile.cookie | SimpleCookie 对象，获取 Cookie 数据
页面跳转 | httpfile.redirect(url=None) | 跳转到某一页面
HTTP头部 | httpfile.start_response(status_code=200, headers=None) | HTTP 返回码和头部

2.2 以下为 httpfile 对象中环境变量（environ）包含的变量对应表
---------------------------------------------------

环境变量 | 描述 | 例子
------- | ------ | ----
REQUEST_METHOD | 请求方法 | GET、POST、PUT、HEAD等
SERVER_PROTOCOL | 请求协议/版本 | HTTP/1.1"
REMOTE_ADDR | 请求客户端的IP地址 | 192.168.1.5
REMOTE_PORT | 请求客户端的端口 | 9999
REQUEST_URI | 完整 uri | /user_info?name=li&age=20
PATH_INFO | 页面地址 | /user_info
QUERY_STRING | 请求参数 | name=li&age=20
CONTENT_TYPE | POST 等报文类型 | application/x-www-form-urlencoded 或 text/html;charset=utf-8
CONTENT_LENGTH | POST 等报文长度 | 1024
HTTP_*_HEADERNAME_* | 其他请求头部 | 如 HTTP_REFERER：https://www.baidu.com/

2.3 部分环境变量也可以使用 httpfile 属性的方式获取
------------------------------------------

环境变量 | 对应属性
------- | -------
PATH_INFO | httpfile.path_Info
QUERY_STRING | httpfile.query_string
REQUEST_URI | httpfile.request_uri
REFERER | httpfile.referer
REQUEST_METHOD | httpfile.request_method
SERVER_PROTOCOL | httpfile.server_protocol

# 3. Mako 文件支持

TODO

# 4. CGI 支持

TODO