from flask import Flask, render_template, Response, jsonify
import cv2
import numpy as np
from gpiozero import LED
from threading import Lock
import serial

app = Flask(__name__)

# =========================
# CAMERA
# =========================
camera = cv2.VideoCapture(0)
camera.set(3, 640)
camera.set(4, 480)

# =========================
# NEXTION
# =========================
try:
    nextion = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
except:
    nextion = None

mode = 1  # 1 = manual, 2 = auto

def send_nextion(cmd):
    if nextion:
        nextion.write(cmd.encode('latin-1') + b'\xff\xff\xff')

# =========================
# MOTORS
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

# =========================
# DETECT ORANGE BALL
# =========================
def detect_orange_ball(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower = np.array([5, 150, 150])
    upper = np.array([20, 255, 255])

    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.erode(mask, None, 2)
    mask = cv2.dilate(mask, None, 2)

    circles = cv2.HoughCircles(
        mask, cv2.HOUGH_GRADIENT, 1, 20,
        param1=50, param2=15,
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
# VIDEO STREAM + AUTO LOGIC
# =========================
def gen_frames():
    global mode

    while True:
        success, frame = camera.read()
        if not success:
            continue

        height, width = frame.shape[:2]

        # =========================
        # DRAW 3 ZONES
        # =========================
        left_x = width // 3
        right_x = 2 * width // 3

        cv2.line(frame, (left_x, 0), (left_x, height), (255,255,255), 2)
        cv2.line(frame, (right_x, 0), (right_x, height), (255,255,255), 2)

        cv2.putText(frame, "LEFT", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

        cv2.putText(frame, "CENTER", (left_x + 20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

        cv2.putText(frame, "RIGHT", (right_x + 20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

        # =========================
        # DETECTION
        # =========================
        circles = detect_orange_ball(frame)
        frame = draw_circles(frame, circles)

        # =========================
        # AUTO MODE
        # =========================
        if mode == 2:
            if circles is not None:
                x, y, r = circles[0]

                if x < left_x:
                    left()
                elif x > right_x:
                    right()
                else:
                    forward()
            else:
                stop()

        # =========================
        # STREAM OUTPUT
        # =========================
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# =========================
# ROUTES
# =========================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/move/<direction>')
def move(direction):
    global mode

    if mode != 1:
        return jsonify({"mode": mode, "move": "blocked"})

    if direction == "w": forward()
    elif direction == "s": backward()
    elif direction == "a": left()
    elif direction == "d": right()
    else: stop()

    return jsonify({"mode": mode, "move": direction})

@app.route('/mode/<int:m>')
def set_mode(m):
    global mode
    mode = m

    if mode == 1:
        send_nextion('t0.txt="Manual"')
    elif mode == 2:
        send_nextion('t0.txt="Auto"')

    return jsonify({"mode": mode})

# =========================
# RUN
# =========================
if __name__ == '__main__':
    send_nextion('t0.txt="Ready"')
    app.run(host='0.0.0.0', port=5000, threaded=True)
