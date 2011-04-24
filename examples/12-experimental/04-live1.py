# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..", ".."))
<<<<<<< HEAD
import warnings
=======
>>>>>>> 2dde5a7eb4a0f379e8d2476487011bdacba7e165

from nodebox.graphics import *

# Live coding example.
# The actual drawing code is in 04-live2.py.
# This script starts the canvas and executes the commands from 04-live2.py.
<<<<<<< HEAD
# You can then edit and save the code there,
# changes will be reflected automatically while the canvas keeps running.
=======
# You can then edit and save the code there, changes will be reflected automatically.
>>>>>>> 2dde5a7eb4a0f379e8d2476487011bdacba7e165

SCRIPT = "04-live2.py"
source = open(SCRIPT).read()
modified = os.path.getmtime(SCRIPT)

def draw(canvas):
    global source
    global modified
<<<<<<< HEAD
    try:
        exec(source)
    except Exception, e:
        warnings.warn(str(e), Warning)
=======
    exec(source)
>>>>>>> 2dde5a7eb4a0f379e8d2476487011bdacba7e165
    if os.path.getmtime(SCRIPT) > modified:
        source = open(SCRIPT).read()
        modified = os.path.getmtime(SCRIPT)
    
canvas.size = 500, 500
canvas.fps = 30
canvas.run(draw)