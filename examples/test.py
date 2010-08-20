# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.append(os.path.join(".."))

from nodebox.graphics import *

def draw(canvas):
    background(1)
    translate(250, 250)
    rotate(canvas.frame)
    rect(-100, -100, 200, 200)
    
canvas.size = 500, 500
canvas.run(draw)
