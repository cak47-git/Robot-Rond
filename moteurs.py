import RPi.GPIO as GPIO
import tkinter as tk
import serial
import time
import threading

# GPIO Setup
GPIO.setmode(GPIO.BCM)


# Le programme contrôle un robot via une interface tkinter sur Raspberry Pi :
# il lit en continu le port série du Nextion pour détecter quel bouton a été pressé 
# (bouton 1 = code 1, bouton 2 = mode normal), 
# gère les moteurs gauche et droit via GPIO selon l'état actuel (avancer, reculer, tourner, arrêt),
# synchronise l'affichage du Nextion avec le texte et les images correspondants, et accepte les commandes clavier 
# (W/A/S/D + espace) ainsi que les boutons tkinter,
# le tout dans un thread séparé pour la lecture série afin de ne pas bloquer l'interface graphique.

#pins
RIGHT_SPEED     = 6
RIGHT_DIRECTION = 5
LEFT_SPEED      = 13
LEFT_DIRECTION  = 26
#ecran
#GPIO14-TX(jaune)
#GPIO15-RX(bleu)
#GND et VCC du raspberry


GPIO.setup(RIGHT_SPEED,     GPIO.OUT)
GPIO.setup(RIGHT_DIRECTION, GPIO.OUT)
GPIO.setup(LEFT_SPEED,      GPIO.OUT)
GPIO.setup(LEFT_DIRECTION,  GPIO.OUT)

nextion = serial.Serial('/dev/serial0', 9600, timeout=1)

def send_nextion(command):
    nextion.write(command.encode('latin-1') + b'\xff\xff\xff')


class RobotController:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Controller")
        self.root.geometry("400x500")
        self.root.configure(bg='#2c3e50')

        self.current_state = 'stopped'
        self.mode = None

        self.status_label = tk.Label(
            root, text="Waiting for mode...",
            font=("Arial", 18, "bold"),
            bg='#2c3e50', fg='#e74c3c', pady=20
        )
        self.status_label.pack()

        control_frame = tk.Frame(root, bg='#2c3e50')
        control_frame.pack(pady=30)

        btn_style = {
            'font': ('Arial', 20, 'bold'), 'width': 5, 'height': 2,
            'bg': '#3498db', 'fg': 'white',
            'activebackground': '#2980b9', 'relief': 'raised', 'bd': 3
        }

        self.btn_forward  = tk.Button(control_frame, text="W\n↑", **btn_style, command=lambda: self.toggle('forward'))
        self.btn_left     = tk.Button(control_frame, text="A\n←", **btn_style, command=lambda: self.toggle('left'))
        self.btn_right    = tk.Button(control_frame, text="D\n→", **btn_style, command=lambda: self.toggle('right'))
        self.btn_backward = tk.Button(control_frame, text="S\n↓", **btn_style, command=lambda: self.toggle('reverse'))

        self.btn_stop = tk.Button(
            control_frame, text="STOP", command=self.emergency_stop,
            font=('Arial', 14, 'bold'), width=5, height=2,
            bg='#e74c3c', fg='white', activebackground='#c0392b',
            relief='raised', bd=3
        )

        self.btn_forward .grid(row=0, column=1, padx=5, pady=5)
        self.btn_left    .grid(row=1, column=0, padx=5, pady=5)
        self.btn_stop    .grid(row=1, column=1, padx=5, pady=5)
        self.btn_right   .grid(row=1, column=2, padx=5, pady=5)
        self.btn_backward.grid(row=2, column=1, padx=5, pady=5)

        self.direction_buttons = {
            'forward': self.btn_forward, 'left': self.btn_left,
            'right':   self.btn_right,   'reverse': self.btn_backward,
        }

        self._key_down = set()
        for key, state in [('w', 'forward'), ('s', 'reverse'), ('a', 'left'), ('d', 'right')]:
            self.root.bind(f'<KeyPress-{key}>',   lambda e, s=state: self._on_keypress(e, s))
            self.root.bind(f'<KeyRelease-{key}>', lambda e, k=key: self._key_down.discard(k))
        self.root.bind('<space>', lambda e: self.emergency_stop())

        tk.Label(
            root,
            text="Press a direction button (or W/A/S/D) to start — press again to stop\n"
                 "Space = Emergency Stop",
            font=("Arial", 10), bg='#2c3e50', fg='#95a5a6',
            pady=10, justify='center'
        ).pack()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        send_nextion('t0.txt="Select Mode"')
        send_nextion('p0.vis=0')

        self._running = True
        threading.Thread(target=self._nextion_listener, daemon=True).start()

    # ── Nextion listener — matches your test.py read style ──────────────────
    def _nextion_listener(self):
        while self._running:
            data = nextion.read(20)          # same as your test.py
            if not data:
                continue
            data_list = list(data)

        # Button ID is at index 2: 1 = button1, 2 = button2
            if data_list == [101, 0, 2, 0, 255, 255, 255]:  # Mode 1 button
                self._set_mode(1)
            elif data_list == [101, 0, 1, 0, 255, 255, 255]:  # Mode 2 button
                self._set_mode(2)

    # ── Mode switching ───────────────────────────────────────────────────────
    def _set_mode(self, mode):
        self.mode = mode
        if mode == 1:
            self._force_stop()
            self.status_label.config(text="Code 1", fg='#e67e22')
            send_nextion('t0.txt="Code 1"')
            send_nextion('p0.vis=0')
        elif mode == 2:
            self._force_stop()
            self.status_label.config(text="Code 2 Ready", fg='#2ecc71')
            send_nextion('t0.txt="Code 2 Ready"')

    def _force_stop(self):
        self._key_down.clear()
        self.current_state = 'stopped'
        GPIO.output(RIGHT_SPEED,     GPIO.LOW)
        GPIO.output(RIGHT_DIRECTION, GPIO.LOW)
        GPIO.output(LEFT_SPEED,      GPIO.LOW)
        GPIO.output(LEFT_DIRECTION,  GPIO.LOW)
        self._highlight_buttons('stopped')

    # ── Key-press handler ────────────────────────────────────────────────────
    def _on_keypress(self, event, state):
        key = event.keysym.lower()
        if key in self._key_down:
            return
        self._key_down.add(key)
        self.toggle(state)

    # ── Toggle — blocked unless mode 2 ──────────────────────────────────────
    def toggle(self, requested_state):
        if self.mode != 2:
            return
        if self.current_state == requested_state:
            self._apply_state('stopped')
        else:
            self._apply_state(requested_state)

    def _apply_state(self, state):
        if state == self.current_state:
            return
        self.current_state = state

        GPIO.output(RIGHT_SPEED,     GPIO.LOW)
        GPIO.output(RIGHT_DIRECTION, GPIO.LOW)
        GPIO.output(LEFT_SPEED,      GPIO.LOW)
        GPIO.output(LEFT_DIRECTION,  GPIO.LOW)

        config = {
            'forward': (True,  True,  True,  True,  "Moving Forward ↑", '#2ecc71', 'Forward',  3),
            'reverse': (True,  False, True,  False, "Moving Reverse ↓", '#9b59b6', 'Reverse',  0),
            'left'   : (True,  True,  False, False, "Turning Left ←",   '#f39c12', 'Left',     1),
            'right'  : (False, False, True,  True,  "Turning Right →",  '#f39c12', 'Right',    2),
            'stopped': (False, False, False, False, "Stopped",          '#e74c3c', 'Stopped',  None),
        }

        r_spd, r_dir, l_spd, l_dir, label, colour, nxt_text, pic_index = config[state]

        GPIO.output(RIGHT_SPEED,     GPIO.HIGH if r_spd else GPIO.LOW)
        GPIO.output(RIGHT_DIRECTION, GPIO.HIGH if r_dir else GPIO.LOW)
        GPIO.output(LEFT_SPEED,      GPIO.HIGH if l_spd else GPIO.LOW)
        GPIO.output(LEFT_DIRECTION,  GPIO.HIGH if l_dir else GPIO.LOW)

        self.status_label.config(text=label, fg=colour)
        send_nextion(f't0.txt="{nxt_text}"')

        if pic_index is not None:
            send_nextion(f'p0.pic={pic_index}')
            send_nextion('p0.vis=1')
        else:
            send_nextion('p0.vis=0')

        self._highlight_buttons(state)

    def _highlight_buttons(self, active_state):
        for state, btn in self.direction_buttons.items():
            if state == active_state:
                btn.config(bg='#27ae60', relief='sunken')
            else:
                btn.config(bg='#3498db', relief='raised')

    def emergency_stop(self):
        if self.mode != 2:
            return
        self._key_down.clear()
        self.current_state = None
        self._apply_state('stopped')
        self.status_label.config(text="EMERGENCY STOP", fg='#e74c3c')
        send_nextion('t0.txt="STOP!"')
        send_nextion('p0.vis=0')

    def on_closing(self):
        self._running = False
        self._force_stop()
        GPIO.cleanup()
        nextion.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = RobotController(root)
    root.mainloop()