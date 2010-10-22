# Add the upper directory (where the nodebox module is) to the search path.
import os, sys;sys.path.insert(0,os.path.join("..",".."))

from nodebox.graphics import *

# A classic NodeBox example (http://nodebox.net/code/index.php/Dendrite).
# It registers the dragged mouse movements,
# and use those to draw wavering lines.
# Thanks to Karsten Wolf.

from random import seed
from math   import sin
 
lines = []

def draw(canvas):
    background(0.1, 0.0, 0.1, 0.25)
    nofill()
    stroke(1, 1, 1, 0.2)
    strokewidth(0.5)
    
    # Register mouse movement.
    if canvas.mouse.dragged:
        lines.append((LINETO, canvas.mouse.x, canvas.mouse.y, canvas.frame))
    elif canvas.mouse.pressed:
        lines.append((MOVETO, canvas.mouse.x, canvas.mouse.y, canvas.frame))  

    if len(lines) > 0:
        for i in range(5):
            seed(i) # Lock the seed for smooth animation.
            p = BezierPath()
            for cmd, x, y, t in lines:
                d = sin((canvas.frame - t) / 10.0) * 10.0 # Play with the numbers.
                x += random(-d, d) 
                y += random(-d, d)
                if cmd == MOVETO:
                    p.moveto(x, y)
                else:
                    p.lineto(x, y)
            drawpath(p)

canvas.fps = 60
canvas.size = 600, 400
#canvas.fullscreen = True
canvas.run(draw)
