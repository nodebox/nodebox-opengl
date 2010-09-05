# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# Load an image from file.
# For performance, it's a good idea to create images once, outside the draw() loop.
# NodeBox can then keep the image in graphics card memory so it displays faster.
img = Image("creature.png")

# A simple image effect is a drop shadow.
# We create a grayscale version of the image with the colorize() filter,
# by reducing the image's R,G,B channels to zero but keeping the alpha channel.
# Then we diffuse it with the blur() filter.
# We create the shadow outside the draw() loop for performance:
shadow = colorize(img, color=(0,0,0,1))
shadow = blur(shadow, amount=3, kernel=5)

def draw(canvas):
    
    canvas.clear()
    
    # Some simple mouse interaction to make it more interesting.
    # Moving the mouse up will move the creature up from the ground.
    dy = canvas.mouse.y
    
    # The origin point (0,0) of the canvas is in the lower left corner.
    # Transformations such as rotate() and scale() originate from (0,0).
    # We move (or "translate") the origin point to the center of the canvas,
    # and then draw the image a bit to the left and to the bottom of it.
    # This way, transformations will originate from the center.
    translate(canvas.width/2, canvas.height/2)
    scale(0.75 + dy*0.001)
    image(img, x=-300, y=-200 + dy*0.1)
    image(shadow, x=-300, y=-240, alpha=0.5 - dy*0.0005)

# Start the application:
canvas.fps  = 60
canvas.size = 500, 500
canvas.run(draw)