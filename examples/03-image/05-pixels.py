# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# The pixels() command yields a list of pixels from a given image.
# Since this is a relatively slow operation, this is not useful for dynamic image processing,
# but there a various other ways in which pixels can be useful. In short:
# - len(Pixels): the number of pixels in the image.
# - Pixels.width: the width of the image.
# - Pixels.height: the height of the image.
# - Pixels[i]: a list of [R,G,B,A] values between 0-255 that can be modified.
# - Pixels.get(x, y): returns a Color from the pixel at row x and column y.
# - Pixels.set(x, y, clr): sets the color of the pixel at (x,y).
# - Pixels.update() commits all the changes. You can then pass Pixels to the image() command.

img = Image("creature.png")
p = Pixels(img)

def draw(canvas):
    
    # Since the background is a bit transparent,
    # it takes some time for the previous frame to fade away.
    background(1,0.03)
    
    # Here we simply use pixels from the image as a color palette.
    for i in range(15):
        x = random(p.width)
        y = random(p.height)
        clr = p.get(x, y)
        clr.alpha *= 0.5
        fill(clr)
        stroke(clr)
        strokewidth(random(5))
        r = random(5, 100)
        ellipse(random(canvas.width), random(canvas.height), r*2, r*2)
    
canvas.size = 500, 500
canvas.run(draw)