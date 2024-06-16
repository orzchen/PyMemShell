import socketio

# standard Python
sio = socketio.Client()

@sio.event
def connect():
    print('Connection established')

@sio.event
def disconnect():
    print('Disconnected from server')

@sio.on('message')
def on_message(data):
    print(f"Message received: {data}")

@sio.on('my_response')
def on_my_response(data):
    print(f"Custom event response received: {data}")

def main():
    sio.connect('http://127.0.0.1:5001/chat')
    sio.send('Hello Server!')
    # sio.emit('my_event', {'data': 'This is a custom event for /my_namespace'})
    # ('join', { 'username': document.getElementById('username').value, 'room': document.getElementById('room').value })
    sio.emit('shell', {'username': 'test', 'room': 'room1'})
    sio.wait()

if __name__ == '__main__':
    main()
