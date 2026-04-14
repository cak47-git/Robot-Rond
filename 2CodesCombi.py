from flask import Flask, render_template, Response, request, jsonify
import cv2
import numpy as np
from gpiozero import LED
from threading import Lock, Thread
import serial

app = Flask(__name__)

# =========================
# CAMERA
# =========================
camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
camera.set(3, 640)
camera.set(4, 480)

# =========================
# NEXTION
# =========================
nextion = serial.Serial('/dev/serial0', 9600, timeout=1)
mode = 0  # 0=none, 1=mode1, 2=manuel

def send_nextion(cmd):
    nextion.write(cmd.encode('latin-1') + b'\xff\xff\xff')

def nextion_listener():
    global mode
    while True:
        data = nextion.read(20)
        if not data:
            continue

        data_list = list(data)

        # Boutons Nextion
        if data_list == [101, 0, 2, 0, 255, 255, 255]:
            mode = 1
            print("Mode 1 (Nextion)")
            send_nextion('t0.txt="Code 1"')
            send_nextion('p0.vis=0')

        elif data_list == [101, 0, 1, 0, 255, 255, 255]:
            mode = 2
            print("Mode 2 (Nextion)")
            send_nextion('t0.txt="Manual"')

# Thread Nextion
Thread(target=nextion_listener, daemon=True).start()

# =========================
# DETECTION BALLE ROUGE
# =========================
def detect_red_ball(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower1 = np.array([0, 100, 100])
    upper1 = np.array([10, 255, 255])
    lower2 = np.array([160, 100, 100])
    upper2 = np.array([180, 255, 255])

    mask = cv2.bitwise_or(
        cv2.inRange(hsv, lower1, upper1),
        cv2.inRange(hsv, lower2, upper2)
    )

    mask = cv2.erode(mask, None, 2)
    mask = cv2.dilate(mask, None, 2)

    gray = cv2.GaussianBlur(mask, (9, 9), 2)

    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, 1, 20,
        param1=50, param2=30,
        minRadius=10, maxRadius=200
    )

    if circles is not None:
        return np.uint16(np.around(circles[0]))
    return None

def draw_circles(frame, circles):
    if circles is not None:
        for x, y, r in circles:
            cv2.circle(frame, (x, y), r, (0,255,0), 2)
            cv2.circle(frame, (x, y), 3, (0,0,255), -1)
    return frame

# =========================
# STREAM VIDEO
# =========================
def gen_frames():
    while True:
        success, frame = camera.read()
        if not success:
            continue

        circles = detect_red_ball(frame)
        frame = draw_circles(frame, circles)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# =========================
# MOTEURS (PRIORITÉ)
# =========================
M1A = LED(27)
M1B = LED(17)
M2A = LED(22)
M2B = LED(23)

lock = Lock()

def forward():
    with lock:
        M1A.on(); M1B.on(); M2A.off(); M2B.off()
        send_nextion('t0.txt="Forward"')

def backward():
    with lock:
        M1A.on(); M1B.on(); M2A.on(); M2B.on()
        send_nextion('t0.txt="Reverse"')

def left():
    with lock:
        M1A.on(); M1B.on(); M2A.on(); M2B.off()
        send_nextion('t0.txt="Left"')

def right():
    with lock:
        M1A.on(); M1B.on(); M2A.off(); M2B.on()
        send_nextion('t0.txt="Right"')

def stop():
    with lock:
        M1A.off(); M1B.off(); M2A.off(); M2B.off()
        send_nextion('t0.txt="STOP"')
        send_nextion('p0.vis=0')

# =========================
# ROUTES FLASK
# =========================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/move/<direction>')
def move_route(direction):
    start = request.args.get('t', default=0, type=float)

    if direction == "w": forward()
    elif direction == "s": backward()
    elif direction == "a": left()
    elif direction == "d": right()
    else: stop()

    return jsonify({"mode": mode, "start": start})

# =========================
# CHANGEMENT MODE (WEB)
# =========================
@app.route('/mode/<int:m>')
def set_mode(m):
    global mode
    mode = m

    if m == 1:
        send_nextion('t0.txt="Code 1"')
        send_nextion('p0.vis=0')
    elif m == 2:
        send_nextion('t0.txt="Manual"')

    return jsonify({"mode": mode})

# =========================
# START
# =========================
if __name__ == '__main__':
    send_nextion('t0.txt="Ready"')
    send_nextion('p0.vis=0')

    app.run(host='0.0.0.0', port=5000, threaded=True)