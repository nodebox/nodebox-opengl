# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

img = Image("creature.png")

def draw(canvas):
    
    # This basically does the same as the previous example (bump),
    # except that we use a twirl distortion filter.
    # Furthermore, the filter is permanently applied when the mouse is pressed.
    # To do this, we replace the source image with the twirled version.
    # Hence we declare img as global, so we can modify the variable's contents.
    global img

    canvas.clear()
    
    dx = canvas.mouse.x / float(img.width)
    dy = canvas.mouse.y / float(img.height)
    image(twirl(img, dx, dy, angle=180, radius=0.5))
    
    if canvas.mouse.pressed:
        # When the mouse is pressed, render a twirled version of the image,
        # and set it as the new source image.
        img = twirl(img, dx, dy, angle=180, radius=0.25)

# Start the application:
canvas.fps  = 60
canvas.size = 500, 500
canvas.run(draw)