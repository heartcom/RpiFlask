import RPi.GPIO as GPIO
from flask import Flask, render_template

app = Flask(__name__)

GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.OUT)

def led_on():
	GPIO.output(4, 1)
	return
def led_off():
	GPIO.output(4, 0)
	return

@app.route('/')
def index():
    print ('index.html START.')
    led_off()
    return render_template('index.html', state='OFF')
	
@app.route('/on/')
def on():
	led_on()
	print ('Switch On')
	return render_template('index.html', state='ON')

@app.route('/off/')
def off():
	led_off()
	print ('Switch Off')
	return render_template('index.html', state='OFF')
		
if __name__=='__main__':
	print('Web Server Starts')
	app.run(debug=False, host='172.30.1.40', port=5000)
	print ('Web Server Ends')

GPIO.cleanup()
print('Program Ends')
