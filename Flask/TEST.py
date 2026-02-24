from flask import Flask, render_template, Response, request
import cv2
import RPi.GPIO as GPIO

app = Flask(__name__)

# =========================
# CONFIG CAMERA
# =========================
camera = cv2.VideoCapture('/dev/video0', cv2.CAP_V4L2)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_FPS, 30)

def gen_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# =========================
# CONFIG MOTEURS
# =========================
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

M1A = 27
M1B = 17
M2A = 22
M2B = 23

GPIO.setup(M1A, GPIO.OUT)
GPIO.setup(M1B, GPIO.OUT)
GPIO.setup(M2A, GPIO.OUT)
GPIO.setup(M2B, GPIO.OUT)

def stop():
    GPIO.output(M1A, False)
    GPIO.output(M1B, False)
    GPIO.output(M2A, False)
    GPIO.output(M2B, False)

def forward():
    GPIO.output(M1A, True)
    GPIO.output(M1B, True)
    GPIO.output(M2A, False)
    GPIO.output(M2B, False)

def backward():
    GPIO.output(M1A, True)
    GPIO.output(M1B, True)
    GPIO.output(M2A, True)
    GPIO.output(M2B, True)

def left():
    GPIO.output(M1A, True)
    GPIO.output(M1B, True)
    GPIO.output(M2A, True)
    GPIO.output(M2B, False)

def right():
    GPIO.output(M1A, True)
    GPIO.output(M1B, True)
    GPIO.output(M2A, False)
    GPIO.output(M2B, True)

# =========================
# ROUTES WEB
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
    if direction == "w":
        forward()
    elif direction == "s":
        backward()
    elif direction == "a":
        left()
    elif direction == "d":
        right()
    else:
        stop()
    return ('', 204)

# =========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
