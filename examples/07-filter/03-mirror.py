# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

img = Image("dendrite.png")

def draw(canvas):
    
    #canvas.clear()
    
    dx = canvas.mouse.x / float(img.width)
    dy = canvas.mouse.y / float(img.height)
    
    # The idea is that the output of each filter can be passed to another filter,
    # creating a "rendering pipeline".
    # For example, the "mirror" effect is a very easy way to show off.
    # It reflects the image along a given horizontal (and/or vertical) axis.
    # In this case, we use the mouse position as axes.
    # By piping together many mirrors, we get an interesting kaleidoscopic effect.
    kaleidoscope = mirror(mirror(img, dx, dy), dy, dx)
    
    # You may have noticed the fluid, blurry transitions between patterns.
    # This is because we are not clearing the canvas background (we are "painting").
    # Since the image gets drawn with an alpha=0.5 (50% opacity),
    # the new version is constantly pasted on top of the previous version.
    image(kaleidoscope, alpha=0.5)

# Start the application.
# Open a window that is as big as the image.
canvas.fps  = 60
canvas.size = img.width, img.height
canvas.run(draw)