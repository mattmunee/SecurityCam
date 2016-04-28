import time
import io
import threading
import picamera
import datetime
import os
import datetime
from collections import deque

class Camera(object):
	streamThread = None  # background thread that reads frames from camera
	recordThread = None
	frame = None  # current frame is stored here by background thread
	last_access = 0  # time of last client access to the camera
	camera = None
	streamPort = 0
	filePort = 2
	keepRecording = False
	circStream = None
	logDirectory = "./ImageLog"
	frameRateHz = 10;
	videoLengthSec = 600;
	totalLogSec = 86400;
	mostNumFrames = 0;
	
	def __init__(self):
		# camera setup
		print '__init__'
		Camera.camera = picamera.PiCamera()
		Camera.camera.resolution = (832, 624)
		Camera.camera.rotation = 270
		Camera.camera.hflip = True
		Camera.camera.vflip = True
		Camera.camera.annotate_background = picamera.Color('black')
		time.sleep(2)
		Camera.camera.start_preview()
		Camera.mostNumFrames = Camera.frameRateHz*Camera.videoLengthSec
		
	def get_frame(self):
		Camera.last_access = time.time()
		if Camera.streamThread is None:
			# start background frame thread
			Camera.streamThread = threading.Thread(target=self._streamThread)
			Camera.streamThread.start()

			# wait until frames start to be available
			while Camera.frame is None:
				time.sleep(0)
		return Camera.frame

	@classmethod
	def _streamThread(cls):
		# let camera warm up
		cls.camera.start_preview()
		time.sleep(2)
		networkStream = io.BytesIO()
		for foo in cls.camera.capture_continuous(networkStream, 'jpeg',use_video_port=True,resize=None,splitter_port=cls.streamPort):
			# store frame
			networkStream.seek(0)
			cls.camera.annotate_text = datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
			cls.frame = networkStream.read()

			# reset stream for next frame
			networkStream.seek(0)
			networkStream.truncate()

			# if there hasn't been any clients asking for frames in
			# the last 10 seconds stop the thread
			if time.time() - cls.last_access > 10:
				break
			
		cls.streamThread = None


	def startRecording(self):
		print 'start recording'
		dt = datetime.datetime.now()
		Camera.logDirectory = "./VideoLogs/%02d%02d%02d_%02d-%02d"%(dt.year,dt.month,dt.day,dt.hour,dt.minute)
		if not os.path.exists(Camera.logDirectory):
			os.makedirs(Camera.logDirectory)
		if Camera.recordThread is None:
			Camera.keepRecording = True
			Camera.recordThread = threading.Thread(target = Camera._recordThread)
			Camera.recordThread.start()	
		time.sleep(2)

	def stopRecording(self):
		print 'stopRecording'
		Camera.keepRecording = False
	
	@classmethod
	def _recordThread(cls):
		print '_recordThread'
		qNames = deque([])
		qTimes = deque([])		
		dt = datetime.datetime.now()
		print "Log Directory is"+cls.logDirectory
		newVidName = "vid_%04d%02d%02d_%02d-%02d-%02d.h264" % (dt.year, dt.month,dt.day,dt.hour,dt.minute,dt.second)
		newFilePath = os.path.join(cls.logDirectory,newVidName)
		print 'Starting First Recording'
		cls.camera.start_recording(newFilePath,format='h264',resize = None,splitter_port = cls.filePort)
		lastStartTime = time.time();
		qNames.append(newFilePath)
		qTimes.append(lastStartTime)
		while(cls.keepRecording):
			dt = datetime.datetime.now()
			cls.camera.annotate_text = dt.strftime('%Y-%m-%d %I:%M:%S %p')
			curTime = time.time()
			if curTime-lastStartTime > cls.videoLengthSec:
				print 'Times Up!'
				if (curTime - qTimes[0])>cls.totalLogSec:
					print 'Log is Full!'
					os.remove(qNames[0]);
					qNames.popleft();
					qTimes.popleft();
				newVidName = "vid_%04d%02d%02d_%02d-%02d-%02d.h264" % (dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second)
				newFilePath = os.path.join(cls.logDirectory,newVidName)
				print "Creating New Recording at "+newFilePath
				cls.camera.split_recording(newFilePath,splitter_port = cls.filePort)
				#cls.camera.stop_recording(cls.filePort)
				#cls.camera.start_recording(newFilePath,format='h264',resize=None,splitter_port = cls.filePort)
				qNames.append(newFilePath)
				qTimes.append(curTime)
				lastStartTime = time.time()
			cls.camera.wait_recording(timeout = 0.1,splitter_port = cls.filePort);
		cls.camera.stop_recording(cls.filePort)
				
				
			
				


