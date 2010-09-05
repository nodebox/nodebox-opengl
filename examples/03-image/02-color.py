# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *
from nodebox.graphics.geometry import smoothstep

img = Image("creature.png")

def draw(canvas):
    
    canvas.clear()

    translate(250, 250)
    scale(0.5)

    t = canvas.frame % 100 * 0.01 # A number between 0.0 and 1.0.
    t = smoothstep(0.0, 1.0, t)   # Slow down ("ease") when nearing 0.0 or 1.0.
    rotate(t * 360)
    
    m = 1.0 - 2 * abs(0.5-t) # A number that goes from 0.0 to 1.0 and then back to 0.0.
    scale(0.5+m)
    
    # The image command has an optional "color" and an optional "alpha" parameter.
    # The alpha sets the overall opacity of the image (alpha=0.25 means 75% transparent).
    # The color adjusts the fill color of the image. By default it is (1,1,1,1),
    # which means that the image pixels are mixed with white and remain unaffected.
    # In this case, we lower the green component,
    # so the creature gets more pink when it flies.
    image(img, x=0, y=-img.height, color=color(1, 1-m, 1, 1), alpha=1.0)
    
    # You can pass a Color object (i.e. returned from color()),
    # or simply a (R,G,B)-tuple, which is faster because no Color needs to be constructed.
        
canvas.size = 500, 500
canvas.run(draw)