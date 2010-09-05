# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# The main purpose of NodeBox for OpenGL is drawing images to the canvas.
# Typically, an image can be a JPEG or TIFF file, or a PNG if it uses transparency.
# Image filenames can be passed to the image() command directly,
# but it is faster to load them before the animation starts:
img = Image("creature.png")

def draw(canvas):
    
    canvas.clear()
    
    # Just like line(), rect(), ellipse() etc. images can be transformed
    # with translate(), scale() and rotate().
    translate(250, 250)
    scale(1.0 + 0.5 * cos(canvas.frame*0.01))    
    rotate(canvas.frame)

    # An image is drawn from its bottom-left corner.
    # So if you draw an image at (0,0), its bottom-left corner is at the canvas origin.
    # By the default the canvas origin is at the bottom-left of the window,
    # but we translated it to the center of the canvas.
    # Then, the image is rotated from the bottom-left corner of the image.
    # We draw it at an offset (minus half the image width and half the image height)
    # so it appears to be rotating from its center.
    image(img, x=-img.width/2, y=-img.height/2)
    
canvas.size = 500, 500
canvas.run(draw)