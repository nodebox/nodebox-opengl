# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# On Mac OS X, you can access the built-in iSight camera with PySight + CocoaSequenceGrabber:
# http://livingcode.blogspot.com/2005/10/pysight-preview.html (Tim Omernick, Dethe Elza)
# This example requires a bit of setup.
# You need to have the Xcode developer tools and PyObjC installed:
# - http://developer.apple.com/technologies/tools/xcode.html
# - http://pyobjc.sourceforge.net/
# You then need to build CocoaSequenceGrabber as a framework with Xcode.
# Open CococaSequenceGrabber/CocoaSequenceGrabber.xcode with Xcode and build it.
# Put the resulting CocoaSequenceGrabber.framework in /Library/Frameworks.
# The PySight folder should be in the same folder as this script.
# You can then access the iSight camera through PyObjC:

from PySight import CSGCamera
from Foundation import NSObject
from PyObjCTools import AppHelper
from time import time

class Camera(object):

    class _delegate(NSObject):
        # CSGCamera delegate grabs frames as a CSGImage, which can be cast to a NSBitmapImageRep.
        def camera_didReceiveFrame_(self, camera, frame):
            self.frame = frame
            AppHelper.stopEventLoop()
    
    def __init__(self, width=320, height=240, fps=30):
        """ Starts the iSight camera with the given size.
        """
        self._delegate = Camera._delegate.alloc().init()
        self._width    = width
        self._height   = height
        self._fps      = fps
        self._time     = 0
        self._camera   = CSGCamera.alloc().init()
        self._camera.startWithSize_((width, height))
        self._camera.setDelegate_(self._delegate)
        

    @property
    def width(self):
        return self._width
        
    @property
    def height(self):
        return self._height
    
    def frame(self):
        """ Returns a frame as a byte string of TIFF image data (or None).
            The byte string can be displayed with image(None, data=Camera.frame()).
        """
        try:
            AppHelper.runConsoleEventLoop(installInterrupt=True)
            return str(self._delegate.frame.representations()[0].TIFFRepresentation().bytes())
        except:
            return None
            
    def stop(self):
        AppHelper.stopEventLoop()
            
camera = Camera(320, 240)

def draw(canvas):
    # A frame from the camera can be passed to the data parameter of the image() command.
    f = camera.frame()
    if f is not None:
        # Draw it with a filter applied.
        # Mac OS X PhotoBooth!
        image(None, data=f, filter=distorted(STRETCH, 
            dx = canvas.mouse.relative_x, 
            dy = canvas.mouse.relative_y))
        
def stop(canvas):
    camera.stop()

canvas.size = camera.width, camera.height
canvas.run(draw, stop=stop)

