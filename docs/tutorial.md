# Introduction 

Litefs is a lite python web framework.

Build a web server framework using Python. Litefs was developed to implement
a server framework that can quickly, securely, and flexibly build Web
projects. Litefs is a high-performance HTTP server. Litefs has the
characteristics of high stability, rich functions, and low system
consumption.

# Installation

It can be installed via pip:

    $ pip install litefs

It can be installed via source code:

    $ git clone https://github.com/leafcoder/litefs.git litefs
    $ cd litefs
    $ python setup.py install

# Quickstart: "Hello world"

Firstly, let's write a basci example via litefs. Save it to "example.py".

    # /usr/bin/env python

    import litefs
    litefs.test_server()

Secondly, you should create a directory named "site" (or any other name
which is same as __"--webroot"__).

    $ mkdir ./site

Thirdly, you can copy the below code into a new file "./site/helloworld.py".

    def handler(self):
        return "Hello World!"

Run "example.py", visit "http://localhost:9090/helloworld" via your browser.
You can see "Hello World!" in your browser.

    $ ./example.py
    Litefs 0.3.0 - January 15, 2020 - 10:46:39
    Starting server at http://localhost:9090/
    Quit the server with CONTROL-C.

# URL ROUTES

The relative path of the python scripts in the "site" folder will be url routes.

For example, we create tow files in "site" folder like below.

## Script route
    # Python route 
    # ./site/hello.py  =>  matches /hello
    def handler(self):
        return 'Hello world'

## Template route

Note: "http" means "self" in handler function.

    # Template route 
    # ./site/cn/hello.mako =>  matches /cn/hello
    <pre>
        PATH_INFO   : ${http.path_info}
        QUERY_STRING: ${http.query_string}
        REQUEST_URI : ${http.request_uri}
        REFERER     : ${http.referer}
        COOKIE      : ${http.cookie}

        hello world
    </pre>

## Static file

    # Other static route => matches /hello.txt
    # ./site/hello.txt
    Hello world

# HTTP Methods

Litefs handlers all methods such as GET, POST, PUT, DELETE or PATCH in
"handler" function.

    def handler(self):
        request_method = self.request_method
        logger.info(request_method)
        return 'request_method: %s' % request_method

# Error Pages

You can set a default 404 page when you start a litefs server.

    $ ./example.py --not-found=not_found.html

# Help

    $ ./example.py --help
    usage: example.py [-h] [--host HOST] [--port PORT] [--webroot WEBROOT]
                    [--debug] [--not-found NOT_FOUND]
                    [--default-page DEFAULT_PAGE] [--cgi-dir CGI_DIR]
                    [--log LOG] [--listen LISTEN]

    Build a web server framework using Python. Litefs was developed to implement a
    server framework that can quickly, securely, and flexibly build Web projects.
    Litefs is a high-performance HTTP server. Litefs has the characteristics of
    high stability, rich functions, and low system consumption. Author: leafcoder
    Email: leafcoder@gmail.com Copyright (c) 2017, Leafcoder. License: MIT (see
    LICENSE for details)

    optional arguments:
    -h, --help            show this help message and exit
    --host HOST           bind server to HOST
    --port PORT           bind server to PORT
    --webroot WEBROOT     use WEBROOT as root directory
    --debug               start server in debug mode
    --not-found NOT_FOUND
                            use NOT_FOUND as 404 page
    --default-page DEFAULT_PAGE
                            use DEFAULT_PAGE as web default page
    --cgi-dir CGI_DIR     use CGI_DIR as cgi scripts directory
    --log LOG             save log to LOG
    --listen LISTEN       server LISTEN


## Context

List attributes of "self".

Attributes                                           | Description
---------------------------------------------------- | -----------
self.environ                                         | 环境变量（只读）
self.environ`[`_*envname*_`]`                        | 获取某环境变量
self.session                                         | session 对象，可临时保存或获取内存数据
self.session_id                                      | session 对象 ID，将通过 SET_COOKIE 环境变量返回给客户端浏览器
self.form                                            | form 为字典对象，保存您提交到服务器的数据
self.config                                          | 服务器的配置对象，可获取初始化服务器的配置信息
self.files                                           | 字典对象，保存上传的文件，格式为：{ *filename1*: *\<StringIO object\>*, *filename2*: *\<StringIO object\>* }
self.cookie                                          | SimpleCookie 对象，获取 Cookie 数据
self.redirect(url=None)                              | 跳转到某一页面
self.start_response(status_code=200, headers=None)   | HTTP 返回码和头部
self.path_Info                                       | PATH_INFO 
self.query_string                                    | QUERY_STRING
self.request_uri                                     | REQUEST_URI
self.referer                                         | REFERER 
self.request_method                                  | REQUEST_METHOD 
self.server_protocol                                 | SERVER_PROTOCOL 
## Environ

环境变量             | 描述                  | 例子
------------------- | --------------------- | ----
REQUEST_METHOD      | 请求方法              | GET、POST、PUT、HEAD等
SERVER_PROTOCOL     | 请求协议/版本         | HTTP/1.1"
REMOTE_ADDR         | 请求客户端的IP地址    | 192.168.1.5
REMOTE_PORT         | 请求客户端的端口      | 9999
REQUEST_URI         | 完整 uri              | /user_info?name=li&age=20
PATH_INFO           | 页面地址              | /user_info
QUERY_STRING        | 请求参数              | name=li&age=20
CONTENT_TYPE        | POST 等报文类型       | application/x-www-form-urlencoded 或 text/html;charset=utf-8
CONTENT_LENGTH      | POST 等报文长度       | 1024
HTTP_*_HEADERNAME_* | 其他请求头部          | 如 HTTP_REFERER：https://www.baidu.com/