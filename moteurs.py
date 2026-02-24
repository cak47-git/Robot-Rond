


import RPi.GPIO as GPIO
import tty
import termios
import sys

# GPIO Setup
GPIO.setmode(GPIO.BCM)
vitesse_droite = 6
vitesse_gauche = 13
direction_droite = 5
direction_gauche = 26

GPIO.setup(vitesse_droite, GPIO.OUT)
GPIO.setup(vitesse_gauche, GPIO.OUT)
GPIO.setup(direction_droite, GPIO.OUT)
GPIO.setup(direction_gauche, GPIO.OUT)

def all_off():
    GPIO.output(vitesse_droite, GPIO.LOW)
    GPIO.output(vitesse_gauche, GPIO.LOW)
    GPIO.output(direction_droite, GPIO.LOW)
    GPIO.output(direction_gauche, GPIO.LOW)

def forward():
    GPIO.output(direction_droite, GPIO.LOW)
    GPIO.output(direction_gauche, GPIO.LOW)
    GPIO.output(vitesse_droite, GPIO.HIGH)
    GPIO.output(vitesse_gauche, GPIO.HIGH)
    print("FORWARD")

def backward():
    GPIO.output(direction_droite, GPIO.HIGH)
    GPIO.output(direction_gauche, GPIO.HIGH)
    GPIO.output(vitesse_droite, GPIO.HIGH)
    GPIO.output(vitesse_gauche, GPIO.HIGH)
    print("BACKWARD")

def left():
    GPIO.output(direction_droite, GPIO.LOW)
    GPIO.output(direction_gauche, GPIO.LOW)
    GPIO.output(vitesse_droite, GPIO.HIGH)   # right motor on
    GPIO.output(vitesse_gauche, GPIO.LOW)    # left motor off
    print("LEFT")

def right():
    GPIO.output(direction_droite, GPIO.LOW)
    GPIO.output(direction_gauche, GPIO.LOW)
    GPIO.output(vitesse_droite, GPIO.LOW)    # right motor off
    GPIO.output(vitesse_gauche, GPIO.HIGH)   # left motor on
    print("RIGHT")

def backward_right():
    GPIO.output(direction_droite, GPIO.HIGH)
    GPIO.output(direction_gauche, GPIO.HIGH)
    GPIO.output(vitesse_droite, GPIO.HIGH)
    GPIO.output(vitesse_gauche, GPIO.LOW)
    print("BACKWARD_RIGHT")

def backward_left():
    GPIO.output(direction_droite, GPIO.HIGH)
    GPIO.output(direction_gauche, GPIO.HIGH)
    GPIO.output(vitesse_droite, GPIO.LOW)
    GPIO.output(vitesse_gauche, GPIO.HIGH)
    print("BACKWARD_LEFT")

def get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return key

print("W=forward  S=backward  A=left  D=right  SPACE=stop  Q=quit")

try:
    while True:
        key = get_key()

        if key in ('\x1b', 'q'):
            print("Quitting...")
            break
        elif key == 'w':
            forward()
        elif key == 's':
            backward()
        elif key == 's' and 'a':
            backward_left()
        elif key == 's'and 'd':
            backward_right()
        elif key == 'a':
            left()
        elif key == 'd':
            right()
        elif key == ' ':
            all_off()
            print("STOP")

except KeyboardInterrupt:
    pass

finally:
    all_off()
    GPIO.cleanup()
