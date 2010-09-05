# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

img = Image("dendrite.png")

def draw(canvas):
    canvas.clear()
    
    # The bloom() and glow() filters can be used for a "magic light" effect.
    # They work as a combination of brightpass(), blur() and add() filters.
    image(bloom(img, 
        intensity = 1.0, 
        threshold = 0.6 - 0.3*canvas.mouse.relative_x))

# Start the application:
canvas.fps  = 30
canvas.size = 700, 350
canvas.run(draw)