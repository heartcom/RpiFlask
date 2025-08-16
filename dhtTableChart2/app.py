from flask import Flask, render_template, jsonify, request
import threading, time, atexit
from collections import deque
import RPi.GPIO as GPIO
import adafruit_dht, board

app = Flask(__name__)

# --- 하드웨어 설정 ---
LED_PIN = 4
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)
_led_state = "OFF"

def led_on():
    global _led_state
    GPIO.output(LED_PIN, 1)
    _led_state = "ON"

def led_off():
    global _led_state
    GPIO.output(LED_PIN, 0)
    _led_state = "OFF"

# --- DHT11 센서 스레드 ---
_dht = adafruit_dht.DHT11(board.D17, use_pulseio=False)
READ_INTERVAL = 3
history = deque(maxlen=500)
sensor_data = {"temp_c": None, "humidity": None, "updated_at": None}
_sensor_lock = threading.Lock()

def _dht_worker():
    global _dht
    while True:
        try:
            t = _dht.temperature
            h = _dht.humidity
            if t is not None and h is not None:
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                t = round(float(t), 1)
                h = round(float(h), 1)
                with _sensor_lock:
                    sensor_data.update({"temp_c": t, "humidity": h, "updated_at": now_str})
                    history.append({"ts": now_str, "temp_c": t, "humidity": h})
        except (RuntimeError, OverflowError):
            pass
        except Exception:
            try: _dht.exit()
            except: pass
            time.sleep(1)
            try: _dht = adafruit_dht.DHT11(board.D17, use_pulseio=False)
            except: pass
        time.sleep(READ_INTERVAL)

threading.Thread(target=_dht_worker, daemon=True).start()

# --- 페이지 라우트 ---
@app.route("/")
def home():
    return page_led()

@app.route("/led")
def page_led():
    with _sensor_lock:
        ts = sensor_data["updated_at"]
    return render_template("led.html", state=_led_state, updated_at=ts)

@app.route("/measure")
def page_measure():
    with _sensor_lock:
        temp = sensor_data["temp_c"]
        humi = sensor_data["humidity"]
        ts = sensor_data["updated_at"]
        rows = list(history)[-200:]
    return render_template("measure.html", temperature=temp, humidity=humi, updated_at=ts, rows=rows)

@app.route("/chart")
def page_chart():
    with _sensor_lock:
        ts = sensor_data["updated_at"]
    return render_template("chart.html", updated_at=ts)

# --- API ---
@app.route("/api/led", methods=["POST"])
def api_led():
    state = (request.json or {}).get("state", "").upper()
    if state == "ON": led_on()
    elif state == "OFF": led_off()
    else: return jsonify(ok=False, error="state must be ON or OFF"), 400
    return jsonify(ok=True, state=_led_state)

@app.route("/api/dht")
def api_dht():
    with _sensor_lock:
        return jsonify(ok=True, **sensor_data)

@app.route("/api/dht-history")
def api_dht_history():
    n = request.args.get("n", type=int) or 200
    with _sensor_lock:
        rows = list(history)[-n:]
    return jsonify(ok=True, rows=rows)

@app.route("/on/")
def on_compat():
    led_on()
    return page_led()

@app.route("/off/")
def off_compat():
    led_off()
    return page_led()

# --- 종료 처리 ---
def _cleanup():
    try: GPIO.cleanup()
    except: pass
    try: _dht.exit()
    except: pass

atexit.register(_cleanup)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
