from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from findee import Findee

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Pathfinder-Findee'
socketio = SocketIO(app)

print("Findee 초기화 중...")
try:
    robot = Findee()
    print("🚀 Pathfinder Robot Control Server Starting...")
except Exception as e:
    print(f"❌ 초기화 오류: {e}")
    sys.exit(1)


@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    print("🚀 Pathfinder Robot Control Server Starting...")
    print(f"📡 Server will be available at: http://{robot.ip}:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)