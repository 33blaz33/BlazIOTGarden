import RPi.GPIO as GPIO # to control our  pins
import threading 		# for pump execution
import datetime			# to get current time
import csv				# for storing and reading sensor values
import random			# for random data generation
import time
import os

#from os.path import exists
from spidev import SpiDev
from flask import Flask, render_template, request, jsonify

#documentation
# https://www.howtogeek.com/167190/how-and-why-to-assign-the-.local-domain-to-your-raspberry-pi/
#https://www.instructables.com/Python-WebServer-With-Flask-and-Raspberry-Pi/
# https://raspberrytips.com/set-new-hostname-raspberry-pi/
# https://learn.adafruit.com/raspberry-pi-analog-to-digital-converters/mcp3008
# https://media.digikey.com/pdf/Data%20Sheets/DFRobot%20PDFs/SEN0193_Web.pdf

# temp sensor
# https://www.arduino.cc/en/uploads/Main/TemperatureSensor.pdf
# https://tutorials-raspberrypi.com/raspberry-pi-temperature-sensor-1wire-ds18b20/
# https://www.adafruit.com/product/165

#scheduler
# https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds

# analog read setup
# https://tutorials-raspberrypi.com/mcp3008-read-out-analog-signals-on-the-raspberry-pi/

# auto start program with crontab
# https://www.itechfy.com/tech/auto-run-python-program-on-raspberry-pi-startup/

# access to rpi via hostname
#https://raspberrypi.stackexchange.com/questions/7640/raspberry-pi-not-reachable-via-its-hostname-in-lan

app = Flask(__name__)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

#define GPIOs
pinWaterPump = 13

# Define GPIO in/out
GPIO.setup(pinWaterPump, GPIO.OUT)   

# initialize pump to off
GPIO.output(pinWaterPump, GPIO.LOW)

# initialize sensor values
sensorHumValue = 0
sensorTmpValue = 0
sensorLgtValue = 0

# initialize constants
SENSOR_LOG_FILE = 'sensorLog.csv'

 
class MCP3008:
    def __init__(self, bus = 0, device = 0):
        self.bus, self.device = bus, device
        self.spi = SpiDev()
        self.open()
        self.spi.max_speed_hz = 1000000 # 1MHz
 
    def open(self):
        self.spi.open(self.bus, self.device)
        self.spi.max_speed_hz = 1000000 # 1MHz
    
    def read(self, channel = 0):
        adc = self.spi.xfer2([1, (8 + channel) << 4, 0])
        data = ((adc[1] & 3) << 8) + adc[2]
        return data
            
    def close(self):
        self.spi.close()


@app.route("/")
def index():
	# Get current time
	now = datetime.datetime.now()
	timeString = now.strftime("%H:%M:%S")
   
	# Read Sensors raw values
	sensorValuesTuple = returnSensorValues()
	sensorHumValue = sensorValuesTuple[0]
	sensorTmpValue = sensorValuesTuple[1]
	sensorLgtValue = sensorValuesTuple[2]
		
	# Refresh values on page
	templateData = {
          'time' : timeString,
	      'humidity' : sensorHumValue,
	      'temperature' : sensorTmpValue,
	      'light' : sensorLgtValue,
        }
      
	# read last 100 sensor measurements and send them to graph
	storedSensorValues = readStoredSensorValues()
	CHART_NR_ELEMENTS = 100
	
	labels = [row[0] for row in storedSensorValues[-CHART_NR_ELEMENTS:]]
	temperatureValues = [row[1] for row in storedSensorValues[-CHART_NR_ELEMENTS:]]
	moistureValues = [row[2] for row in storedSensorValues[-CHART_NR_ELEMENTS:]]
	lightValues = [row[3] for row in storedSensorValues[-CHART_NR_ELEMENTS:]]

	
	return render_template('index.html', **templateData,
		labels=labels, 
		temperatureValues=temperatureValues, 
		moistureValues=moistureValues, 
		lightValues=lightValues)
	
	
#background process happening without any refreshing
@app.route('/turnWaterPumpOn/<delay>')
def turnWaterPumpOn(delay):
			
	# Get current time
	now = datetime.datetime.now()
	timeString = now.strftime("%H:%M:%S")
	
	# Read Sensors raw values
	sensorValuesTuple = returnSensorValues()
	sensorHumValue = sensorValuesTuple[0]
	sensorTmpValue = sensorValuesTuple[1]
	sensorLgtValue = sensorValuesTuple[2]

	# Turn pup on/off
	print("Pumping time [s]: " + str(delay))
	turnWatherPump(GPIO.HIGH)
	t = threading.Timer(int(delay), lambda: turnWatherPump(GPIO.LOW))
	t.start()

	# Refresh values on page
	templateData = {
          "time" : timeString,
	      "humidity" : sensorHumValue,
	      "temperature" : sensorTmpValue,
	      "light" : sensorLgtValue
        }
	
	return jsonify(templateData)

def turnWatherPump(status):
	print("Turn pump: " + str(status))
	GPIO.output(pinWaterPump, status)
		
def storeSensorValues():
	print("Storing sensor values")
	now = datetime.datetime.now()
	now = now.strftime("%H:%M:%S %d.%m.%Y")
	
	# Read Sensors raw values
	sensorValuesTuple = returnSensorValues()
	sensorHumValue = sensorValuesTuple[0]
	sensorTmpValue = sensorValuesTuple[1]
	sensorLgtValue = sensorValuesTuple[2]
		
	# Prepare row to append
	row = [str(now), str(sensorTmpValue), str(sensorHumValue), str(sensorLgtValue)]
	
	# Open file in append mode and append row
	with open(SENSOR_LOG_FILE, 'a+') as csvfile:
		writer = csv.writer(csvfile, delimiter=';')
		writer.writerow(row)
		print(row)

def readStoredSensorValues():
	data = [];
	
	fileExists = os.path.exists(SENSOR_LOG_FILE)
	if fileExists:
		try:
			with open(SENSOR_LOG_FILE, 'r') as csvfile:
				reader = csv.reader(csvfile, delimiter=';')
		
				for line in reader:
					data.append(line)
		except Exception as ex:
			# Delete file becasue file might be corupted from unexpected shout down
			os.remove(SENSOR_LOG_FILE)
		
	return data

def returnSensorValues():
	# init analog to digital converter
	adc = MCP3008()
   
	# Read Sensors Status
	sensorHumRaw = adc.read(channel = 0)
	sensorTmpRaw = adc.read(channel = 1)
	sensorLgtRaw = adc.read(channel = 2)
	
	#Voltage to 0%-100% from 0.82min voltage and 2.80 max voltage
	DRY = 815		# max dry voltage
	WET = 255		# max wet voltage
	mappedValue = map_values(sensorHumRaw, WET, DRY, 0, 100)
	mappedValue = 1 if mappedValue==0 else mappedValue
	sensorHumValue = round(1/ mappedValue* 100,1)

	
	# Voltage to celsius, 0.5 is offset
	sensorTmpVoltage = sensorTmpRaw / 1023.0 * 3.3
	sensorTmpValue = round((sensorTmpVoltage - 0.5) * 100.0,1)
	
	# Light sensor
	sensorLgtValue = map_values(sensorLgtRaw, 0, 1024, 0, 100)
	
	print("------------------- Sensor values -------------------")
	print(f"Sensor value Humidity [%]:\t{sensorHumValue} \tRaw\t{round(sensorHumRaw,3)}")
	print(f"Sensor value Temperature [C]:\t{sensorTmpValue} \tVoltage\t{round(sensorTmpVoltage,3)}")
	print(f"Sensor value Light [%]:\t\t{sensorLgtValue}	Raw\t{round(sensorLgtRaw,3)}")
	print("")
	
	return sensorHumValue, sensorTmpValue, sensorLgtValue

def map_values(x, in_min, in_max, out_min, out_max):
	return int((x-in_min) *  (out_max-out_min) / (in_max-in_min) + out_min)

def every(delay, task):
	next_time = time.time() + delay
	while True:
		time.sleep(max(0, next_time - time.time()))
		task()
		
		# skip tasks if we are behind schedule:
		next_time += (time.time() - next_time) // delay * delay + delay

# Store sensor data every 15 min
threading.Thread(target=lambda:every(15*60, storeSensorValues), daemon=True).start()


if __name__ == "__main__":
	#threading.Timer(10, storeSensorValues).start()
	app.run(host='0.0.0.0', port=80, debug=False)
