# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# This example will make more sense after you've seen the examples in /07-filter

# NodeBox for OpenGL has a range of commands for filtering images.
# For example, blur(img) returns a new Image that is a blurred version of the given image.
# By chaining filters, e.g. twirl(bump(blur(img))), interesting effects can be achieved

# Some filters can be used directly with the image() command.
# For the filters invert(), colorize(), blur(), desaturate(), mask(), blend() and distort(),
# there are variants inverted(), colorized(), blurred(), desaturated(), masked(),
# blended() and distorted() that can be passed to the "filter" parameter of the image() command.
# The advantage is that the effect doesn't need to be rendered offscreen, which is faster.
# The disadvantage is that:
# - image() parameters "color" and "alpha" won't work (they are overridden by the filter),
# - the effect can not be chained,
# - the effect must be relatively simple, e.g. blurred() is a 3x3 Gaussian kernel
#   vs. blur() which uses a 9x9 Gaussian kernel.

# In short, these variants are usually meant for testing purposes,
# but it's useful to note their existence nonetheless.

img = Image("creature.png")

def draw(canvas):
    
    canvas.clear()

    image(img, 50, 50, filter=distorted(STRETCH, dx=canvas.mouse.relative_x,
                                                 dy=canvas.mouse.relative_y))
        
canvas.size = 500, 500
canvas.run(draw)