import RPi.GPIO as GPIO
import time
import subprocess
 
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.OUT)
GPIO.setup(17, GPIO.OUT)
 
GPIO.setup(22, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)
 
 
while True:
    commande = input("Entrez une commande: ").strip()
    if commande == "s":
            GPIO.output(27, True)
            GPIO.output(17, True)
            GPIO.output(22, True)
            GPIO.output(23, True)
    elif commande == "w":
            GPIO.output(27, True)
            GPIO.output(17, True)
            GPIO.output(22, False)
            GPIO.output(23, False)
    elif commande == "a":
            GPIO.output(27, True)
            GPIO.output(17, False)
    elif commande == "d":
            GPIO.output(27, False)
            GPIO.output(17, True)
    else :
            GPIO.output(27, False)
            GPIO.output(17, False)
 
        
 