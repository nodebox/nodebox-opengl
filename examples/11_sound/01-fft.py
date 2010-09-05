# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *
from nodebox.sound import PD, LOCALHOST

# PureData is a free, real-time graphical programming environment for audio processing.
# You can connect building blocks to manipulate audio input, or generate audio output.
# A network of building blocks is called a "patch" in Pd-terms.

# FFT (Fast Fourier Transform) is (among other things) an algorithm to measure tone frequency.
# The 01-fft.pd patch calculates FFT on the microphone input and broadcasts 
# a list of 8 frequency bands (from low tones to high tones) on the "/equalizer" path. 
# You can observe this by opening the PD patch.
# We can retrieve the data with PD.get("/equalizer").

# This is useful for an interactive VJ application, for example.

# The nodebox.sound.PD class is useful for loading a patch silently in the background.
# The buffer is the number of bytes of audio to transfer between NodeBox and Pd during each request.
# FFT requires a lot of computation, so small buffers are best.
# With start=True to patch will load automatically. Be patient while it loads.
pd = PD("01-fft.pd", buffer=16, start=True)

def draw(canvas):
    canvas.clear()
    # Retrieve new audio frequencies each frame of animation.
    # The server host and port correspond to the host and port in the patch.
    data = pd.get("/equalizer", host=LOCALHOST, port=44000)
    if data:
        w = float(canvas.width) / len(data)
        for i, frequency in enumerate(data):
            rect(w*i, 0, w, frequency * 2)

# We can register a stop() event with the canvas,
# which will be executed when the application window closes.
# It is important to quit PD here, otherwise it will continue to run in the background!
def stop(canvas):
    pd.stop()

canvas.run(draw, stop=stop)

