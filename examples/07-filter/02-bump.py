# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

img = Image("creature.png")

def draw(canvas):
    
    canvas.clear()
    
    # The mouse position controls the origin of the bulge.
    # The bump() filter takes two parameters: dx and dy (as do most distortion filters).
    # These control the origin of the bulge, as relative values between 0.0 and 1.0.
    # For example: dx=0.0 means left edge, dx=0.5 means center of image.
    # We divide the absolute mouse position by the image width to get relative values.
    dx = canvas.mouse.x / float(img.width)
    dy = canvas.mouse.y / float(img.height)
    
    # Since the effect is interactive, we can't render it beforehand.
    # We need to reapply it to the source image each frame, 
    # based on the current mouse position in this frame.
    image(bump(img, dx, dy, radius=0.5, zoom=0.75))
    
    # The opposite of bump() is dent():
    #image(dent(img, dx, dy, radius=0.5, zoom=0.75))

# Start the application:
canvas.fps  = 60
canvas.size = 500, 500
canvas.run(draw)