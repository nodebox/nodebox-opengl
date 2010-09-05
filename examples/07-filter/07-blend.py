# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# Blend modes are used to combine the pixels of two images,
# in different ways than standard transparency.
# NodeBox supports the most common blend modes as filters:
# add(), subtract(), darken(), lighten(), multiply(), screen(), overlay(), hue().
# These can be used to adjust the lighting in an image
# (by blending it with a copy of itself),
# or to obtain many creative texturing effects.

img1 = Image("creature.png")
img2 = Image("creature.png")

def draw(canvas):
    
    canvas.clear()
    
    # Press the mouse to compare the blend to normal ("source over") mode:
    if not canvas.mouse.pressed:
        image( 
            # Try changing this to another blend filter:
            multiply(img1, img2, 
            # All blend modes (and mask()) have optional dx and dy parameters
            # that define the offset of the blend layer.
                dx = canvas.mouse.x - img1.width/2, 
                dy = canvas.mouse.y - img1.height/2))
    else:
        image(img1)
        image(img2, 
            x = canvas.mouse.x - img1.width/2, 
            y = canvas.mouse.y - img1.height/2)

# Start the application:
canvas.fps  = 30
canvas.size = 500, 500
canvas.run(draw)