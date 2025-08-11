import threading
import time
import atexit

import RPi.GPIO as GPIO
from flask import Flask, render_template, jsonify
import adafruit_dht
import board

app = Flask(__name__)

# =======================
# LED 설정 (BCM GPIO 4)
# =======================
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

# =========================================
# DHT 센서 설정 (DHT11 on GPIO4) - 스레드
# =========================================
# DHT11 사용
_dht = adafruit_dht.DHT11(board.D17, use_pulseio=False)

READ_INTERVAL = 3  # 3초마다 읽기

sensor_data = {
    "temp_c": None,
    "humidity": None,
    "updated_at": None,
}
_sensor_lock = threading.Lock()

def _dht_worker():
    """3초마다 DHT 센서를 읽어 최신값을 보관"""
    global _dht
    while True:
        try:
            t = _dht.temperature
            h = _dht.humidity
            if t is not None and h is not None:
                with _sensor_lock:
                    sensor_data["temp_c"] = round(float(t), 1)
                    sensor_data["humidity"] = round(float(h), 1)
                    sensor_data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        except (RuntimeError, OverflowError):
            # DHT 특성상 간헐적 오류는 정상 → 무시 후 재시도
            pass
        except Exception:
            # 드물게 장치 초기화가 필요할 수 있음 → 재생성
            try:
                _dht.exit()
            except Exception:
                pass
            time.sleep(1.0)
            try:
                _dht = adafruit_dht.DHT11(board.D4, use_pulseio=False)
            except Exception:
                pass
        time.sleep(READ_INTERVAL)

# 스레드 시작
_thread = threading.Thread(target=_dht_worker, daemon=True)
_thread.start()

# =======================
# Flask Routes
# =======================
@app.route('/')
def index():
    with _sensor_lock:
        temp = sensor_data["temp_c"]
        humi = sensor_data["humidity"]
        ts = sensor_data["updated_at"]
    return render_template(
        'index.html',
        state=_led_state,
        temperature=temp,
        humidity=humi,
        updated_at=ts
    )

@app.route('/on/')
def on():
    led_on()
    return index()

@app.route('/off/')
def off():
    led_off()
    return index()

# 값만 주는 API (자동 갱신용)
@app.route('/api/dht')
def api_dht():
    with _sensor_lock:
        return jsonify(
            ok=True,
            temp_c=sensor_data["temp_c"],
            humidity=sensor_data["humidity"],
            updated_at=sensor_data["updated_at"],
        )

# 종료 시 정리
def _cleanup():
    try:
        GPIO.cleanup()
    except Exception:
        pass
    try:
        _dht.exit()
    except Exception:
        pass

atexit.register(_cleanup)

if __name__ == '__main__':
    print('Web Server Starts')
    # 외부 접속 허용: host='0.0.0.0' (내부 전용이면 127.0.0.1)
    app.run(debug=False, host='0.0.0.0', port=5000)
