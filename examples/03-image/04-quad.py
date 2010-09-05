# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

img = Image("creature.png")

# The image.quad property describes the four-sided polygon 
# on which an image texture is "mounted".
# This is not necessarily a rectangle, the corners can be distorted:
img.quad.dx1 =  200
img.quad.dy1 =  100
img.quad.dx2 =  100
img.quad.dy2 = -100

# This flushes the image cache, so it is a costly operation.

def draw(canvas):
    canvas.clear()
    image(img)
    
canvas.size = 500, 500
canvas.run(draw)