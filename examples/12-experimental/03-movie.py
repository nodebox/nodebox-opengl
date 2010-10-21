# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..", ".."))

import tempfile
import subprocess
import shutil

class MovieEncoderError(Exception):
    pass

class Movie:
    
    def __init__(self, canvas, encoder="ffmpeg"):
        """ Creates a movie recorder for the given Canvas.
            Saving the movie requires ffmpeg (http://www.ffmpeg.org/).
            The encoder parameter specifies the path to the ffmpeg executable.
        """
        # You need to compile and build ffmpeg from source.
        # However, if you're on Mac OS X 10.3-5 we have a precompiled binary at:
        # http://cityinabottle.org/media/download/ffmpeg-osx10.5.zip
        # If you place it in the same folder as this script, set encoder="./ffmpeg".
        # This binary was obtained from ffmpegX.
        # Binaries for Win32 can also be found online.
        self._canvas  = canvas
        self._frames  = tempfile.mkdtemp()
        self._encoder = encoder
    
    def record(self):
        """ Call Movie.record() in Canvas.draw() to add the current frame to the movie.
            Frames are stored as PNG-images in a temporary folder until Movie.save() is called.
        """
        self._canvas.save(os.path.join(self._frames, "%09d.png" % self._canvas.frame))
        
    def save(self, path):
        """ Saves the movie at the given path (e.g. "test.mp4").
            Raises MovieEncoderError if unable to launch ffmpeg from the shell.
        """
        try:
            f = os.path.join(self._frames, "%"+"09d.png") # Option -y overwrites exising files.
            p = subprocess.Popen([self._encoder, "-y", "-i", f, path], stderr=subprocess.PIPE)
            p.wait()
            self.close()
        except:
            raise MovieEncoderError
        
    def close(self):
        try: shutil.rmtree(self._frames)
        except:
            pass

    def __del__(self):
        try: shutil.rmtree(self._frames)
        except:
            pass

from nodebox.graphics import *

movie = Movie(canvas)

def draw(canvas):
    canvas.clear()
    background(1)
    translate(250, 250)
    rotate(canvas.frame)
    rect(-100, -100, 200, 200)
    movie.record() # Capture each frame.
    
canvas.size = 500, 500
canvas.run(draw)

movie.save("test.mp4")
movie.close()
