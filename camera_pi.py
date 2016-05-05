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
	lock=threading.Lock()
	
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
		print 'Camera Settings:'
		print 'ISO: ', Camera.camera.iso
		print 'awb_mode: ', Camera.camera.awb_mode
		print 'brightness: ', Camera.camera.brightness
		print 'exp_comp: ', Camera.camera.exposure_compensation
		print 'exp_mode: ', Camera.camera.exposure_mode
		print 'image_denoise: ', Camera.camera.image_denoise
		print 'video_denoise: ', Camera.camera.video_denoise
		
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
		lastCall = time.time()
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
		Camera.logDirectory = "./VideoLogs/%02d%02d%02d_%02d-%02d-%02d"%(dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second)
		print 'Log Path: ',os.path.abspath(Camera.logDirectory)
		if not os.path.exists(Camera.logDirectory):
			os.makedirs(Camera.logDirectory)
		Camera.keepRecording = True
		if Camera.recordThread is None:
			print 'Record Thread None'
			Camera.recordThread = threading.Thread(target = Camera._recordThread)
			Camera.recordThread.start()	
		else:
			try:
				if not Camera.recordThread.isAlive():
					print 'Record Thread Already Exists'
					Camera.recordThread=None
					self.startRecording()
			except:
				pass
		time.sleep(2)

	def stopRecording(self):
		print 'stopRecording'
		Camera.keepRecording = False


	def archiveVideoLog(self):
		print 'archiving log'
		Camera.keepRecording = False
		while Camera.recordThread.isAlive():
			print 'Camera still alive'
			time.sleep(0.2)
		print 'Restarting Log'
		self.startRecording()

	@classmethod
	def _recordThread(cls):
		print '_recordThread'
		qNames = deque([])
		qTimes = deque([])		
		dt = datetime.datetime.now()
		print "Log Directory is"+os.path.abspath(cls.logDirectory)
		newVidName = "vid_%04d%02d%02d_%02d-%02d-%02d.h264" % (dt.year, dt.month,dt.day,dt.hour,dt.minute,dt.second)
		newFilePath = os.path.join(cls.logDirectory,newVidName)
		print 'Starting First Recording'
		cls.camera.start_recording(newFilePath,format='h264',resize = None,splitter_port = cls.filePort)
		lastStartTime = time.time();
		qNames.append(newFilePath)
		qTimes.append(lastStartTime)
		while(cls.keepRecording):
			print 'Record Thread: keepRecording=',cls.keepRecording
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
				qNames.append(newFilePath)
				qTimes.append(curTime)
				lastStartTime = time.time()
			cls.camera.wait_recording(timeout = 0.1,splitter_port = cls.filePort);
		Camera.camera.stop_recording(Camera.filePort)


