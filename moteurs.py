import RPi.GPIO as GPIO
import tkinter as tk
import serial

# GPIO Setup
GPIO.setmode(GPIO.BCM)

# Right motor pins
RIGHT_SPEED = 6
RIGHT_DIRECTION = 5

# Left motor pins
LEFT_SPEED = 13
LEFT_DIRECTION = 26

GPIO.setup(RIGHT_SPEED, GPIO.OUT)
GPIO.setup(RIGHT_DIRECTION, GPIO.OUT)
GPIO.setup(LEFT_SPEED, GPIO.OUT)
GPIO.setup(LEFT_DIRECTION, GPIO.OUT)

# Nextion serial setup
nextion = serial.Serial('/dev/serial0', 9600, timeout=1)

def send_nextion(command):
    """Send a command to the Nextion screen."""
    nextion.write((command + '\xff\xff\xff').encode('latin-1'))


class RobotController:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Controller")
        self.root.geometry("400x500")
        self.root.configure(bg='#2c3e50')

        # Toggle state: one of 'forward', 'reverse', 'left', 'right', 'stopped'
        self.current_state = 'stopped'

        # ── Status label ────────────────────────────────────────────────────
        self.status_label = tk.Label(
            root,
            text="Stopped",
            font=("Arial", 18, "bold"),
            bg='#2c3e50',
            fg='#e74c3c',
            pady=20
        )
        self.status_label.pack()

        # ── Button grid ─────────────────────────────────────────────────────
        control_frame = tk.Frame(root, bg='#2c3e50')
        control_frame.pack(pady=30)

        btn_style = {
            'font': ('Arial', 20, 'bold'),
            'width': 5,
            'height': 2,
            'bg': '#3498db',
            'fg': 'white',
            'activebackground': '#2980b9',
            'relief': 'raised',
            'bd': 3
        }

        self.btn_forward  = tk.Button(control_frame, text="W\n↑",  **btn_style, command=lambda: self.toggle('forward'))
        self.btn_left     = tk.Button(control_frame, text="A\n←",  **btn_style, command=lambda: self.toggle('left'))
        self.btn_right    = tk.Button(control_frame, text="D\n→",  **btn_style, command=lambda: self.toggle('right'))
        self.btn_backward = tk.Button(control_frame, text="S\n↓",  **btn_style, command=lambda: self.toggle('reverse'))

        self.btn_stop = tk.Button(
            control_frame,
            text="STOP",
            command=self.emergency_stop,
            font=('Arial', 14, 'bold'),
            width=5, height=2,
            bg='#e74c3c', fg='white',
            activebackground='#c0392b',
            relief='raised', bd=3
        )

        self.btn_forward .grid(row=0, column=1, padx=5, pady=5)
        self.btn_left    .grid(row=1, column=0, padx=5, pady=5)
        self.btn_stop    .grid(row=1, column=1, padx=5, pady=5)
        self.btn_right   .grid(row=1, column=2, padx=5, pady=5)
        self.btn_backward.grid(row=2, column=1, padx=5, pady=5)

        # Keep refs for highlight updates
        self.direction_buttons = {
            'forward': self.btn_forward,
            'left':    self.btn_left,
            'right':   self.btn_right,
            'reverse': self.btn_backward,
        }

        # ── Keyboard bindings (one press = toggle, no held-key spam) ────────
        # Use KeyPress only; ignore auto-repeat with a simple guard
        self._key_down = set()
        for key, state in [('w', 'forward'), ('s', 'reverse'),
                            ('a', 'left'),   ('d', 'right')]:
            self.root.bind(f'<KeyPress-{key}>',
                           lambda e, s=state: self._on_keypress(e, s))
            self.root.bind(f'<KeyRelease-{key}>',
                           lambda e, k=key: self._key_down.discard(k))

        self.root.bind('<space>', lambda e: self.emergency_stop())

        # ── Instructions ────────────────────────────────────────────────────
        tk.Label(
            root,
            text="Press a direction button (or W/A/S/D) to start — press again to stop\n"
                 "Space = Emergency Stop",
            font=("Arial", 10),
            bg='#2c3e50', fg='#95a5a6',
            pady=10, justify='center'
        ).pack()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Initial Nextion message (sent only once at startup)
        send_nextion('t0.txt="Ready"')

    # ── Key-press handler — ignores OS key-repeat ────────────────────────────
    def _on_keypress(self, event, state):
        key = event.keysym.lower()
        if key in self._key_down:          # OS auto-repeat → ignore
            return
        self._key_down.add(key)
        self.toggle(state)

    # ── Core toggle logic ────────────────────────────────────────────────────
    def toggle(self, requested_state):
        """If already in requested_state → stop. Otherwise → move."""
        if self.current_state == requested_state:
            self._apply_state('stopped')
        else:
            self._apply_state(requested_state)

    def _apply_state(self, state):
        """Apply motor outputs and update UI/Nextion ONLY when state changes."""
        if state == self.current_state:
            return                          # nothing changed — no serial spam

        self.current_state = state

        # Reset all outputs first
        GPIO.output(RIGHT_SPEED,     GPIO.LOW)
        GPIO.output(RIGHT_DIRECTION, GPIO.LOW)
        GPIO.output(LEFT_SPEED,      GPIO.LOW)
        GPIO.output(LEFT_DIRECTION,  GPIO.LOW)

        config = {
            # state        : (R_spd, R_dir, L_spd, L_dir,  label_text,          label_colour,  nextion_text)
            'forward' : (True,  True,  True,  True,  "Moving Forward ↑",  '#2ecc71', 'Forward'),
            'reverse' : (True,  False, True,  False, "Moving Reverse ↓",  '#9b59b6', 'Reverse'),
            'left'    : (True,  True,  False, False, "Turning Left ←",    '#f39c12', 'Left'),
            'right'   : (False, False, True,  True,  "Turning Right →",   '#f39c12', 'Right'),
            'stopped' : (False, False, False, False, "Stopped",           '#e74c3c', 'Stopped'),
        }

        r_spd, r_dir, l_spd, l_dir, label, colour, nxt = config[state]

        GPIO.output(RIGHT_SPEED,     GPIO.HIGH if r_spd else GPIO.LOW)
        GPIO.output(RIGHT_DIRECTION, GPIO.HIGH if r_dir else GPIO.LOW)
        GPIO.output(LEFT_SPEED,      GPIO.HIGH if l_spd else GPIO.LOW)
        GPIO.output(LEFT_DIRECTION,  GPIO.HIGH if l_dir else GPIO.LOW)

        self.status_label.config(text=label, fg=colour)
        send_nextion(f't0.txt="{nxt}"')     # ← sent ONCE per state change

        self._highlight_buttons(state)

    def _highlight_buttons(self, active_state):
        """Light up the active direction button; reset the others."""
        for state, btn in self.direction_buttons.items():
            if state == active_state:
                btn.config(bg='#27ae60', relief='sunken')
            else:
                btn.config(bg='#3498db', relief='raised')

    # ── Emergency stop ───────────────────────────────────────────────────────
    def emergency_stop(self):
        self._key_down.clear()
        self._apply_state('stopped')        # dedup guard still applies
        self.status_label.config(text="EMERGENCY STOP", fg='#e74c3c')
        send_nextion('t0.txt="STOP!"')      # override with urgent message

    # ── Clean shutdown ───────────────────────────────────────────────────────
    def on_closing(self):
        self.emergency_stop()
        GPIO.cleanup()
        nextion.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = RobotController(root)
    root.mainloop()