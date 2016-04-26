from flask import Flask, request, render_template, redirect, url_for, Response, current_app
from camera_pi import Camera
from multiprocessing import Process
import time
from threading import Thread
import sys

app = Flask(__name__)

timeOut = 1200
accessGranted = False
startTime = time.time();
killall = False
camera = Camera()
userInputReceived = False
server = None

def run_server():
	app.run(host = '0.0.0.0',use_reloader = False, debug = False)

def accessTimer():
	global timeOut
	global accessGranted
	global startTime
	global killall
	print "Access Timer Started"
	while(not(killall)):
		time.sleep(0.5)
		elapsedTime = time.time()-startTime
		print 'Next Iteration, killall',killall, elapsedTime, accessGranted
		if (elapsedTime>timeOut) and accessGranted:
			print "Access Expired"
			accessGranted = False;
			index()
	print "Ending Thread"
	
def getInput():
	input_var = raw_input('Enter Something: ')
	print 'Input Received'
	global userInputReceived
	userInputReceived = True

def cleanupApp():
	global server
	
	killall=True
	print "Waiting for kills"
	time.sleep(3)
	print "Should be dead"
	camera.stopRecording()
	print 'Finished!'
	#server.terminate()
	#server.join()
	time.sleep(1)


@app.route('/')
def index():
	print "Index Requested"
	return redirect('/login')
		
# route for handling the login page logic
@app.route('/login', methods=['GET', 'POST'])
def login():
	global accessGranted
	global startTime
	print "Login Requested"
	error = None
	if request.method == 'POST':
		if request.form['username'] != 'the.reaveses' or request.form['password'] != 'redr00ster':
			error = 'Invalid Credentials. Please try again.'
			accessGranted = False
		else:
			print "Access Granted"
			accessGranted = True
			startTime = time.time()
			return redirect(url_for('feed'))
	return render_template('login.html', error=error)
    
@app.route('/feed')
def feed():
	"""Live Video Feed """
	global accessGranted
	print "/feed Requested"
	print accessGranted
	if accessGranted:
		return render_template('index.html')
	else:
		return redirect(url_for('login'))


def gen(camera_inst):
    """Video streaming generator function."""
    while True:
        frame = camera_inst.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
	"""Video streaming route. Put this in the src attribute of an img tag."""
	global camera
	if accessGranted:
		return Response(gen(camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
	else:
		return redirect(url_for('login'))
	
if __name__=='__main__':
	try:
		print "Restarting..."
		killall=True
		print "Waiting for kills"
		time.sleep(2)
		print "Should be dead"
		killall=False

		t=Thread(target = accessTimer,args = ())
		t.setDaemon(True)
		t.start()
		
		t2=Thread(target = getInput,args = ())
		t2.setDaemon(True)
		t2.start()
		
		camera.startRecording()
		
		print 'About to run'
		app.run(host = '0.0.0.0',use_reloader = False, debug = False)
		#server = Process(target=run_server)
		#server.start()
		
		while not userInputReceived:
			time.sleep(1)
		
		cleanupApp()
			
		
	except KeyboardInterrupt:
		print 'Received KeyboardInterrupt'
		camera.stopRecording()
		time.sleep(4)
		killall = True
		sys.exit()
	
