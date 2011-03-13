# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..", ".."))

from nodebox.graphics import *
from pyglet.gl import *
from random import seed

# A question that regularly pops up is:
# "How can I draw shapes to the canvas with a blending mode? (e.g. multiply)"
# OpenGL has different blend modes with the glBlendFunc() command.
# You can either enable alpha transparency (for images with holes)
# OR a different blend mode, but you cannot combine both.
# This is a limitation in OpenGL.
# You could use image filters (e.g. multiply(), render()) but this can be slow / a lot of work:
# if you also want your image to appear rotated on the canvas,
# you'd first need to transform (rotate, scale) the image into another image,
# and then use this rendered image with multiply() or screen().

# Here is an example of additive and subtractive blending, directly to the canvas.
# You can use these to simulate screen and multiply blend.
#    Additive: glBlendFunc(GL_SRC_ALPHA, GL_ONE)
# Subtractive: glBlendFunc(GL_DST_COLOR, GL_ONE)

# Additive blending works OK with alpha transparency,
# subtractive doesn't, so it's only useful in specific situations.

def draw(canvas):

    seed(1)
    canvas.clear()
    background(0)

    if not canvas.mouse.pressed:
        # Press the mouse to see the difference with normal blending.
        # Additive mode adds a nice glow effect to overlapping shapes.
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        #glBlendFunc(GL_DST_COLOR, GL_ZERO) # For subtractive blending, set background(1).
                                            # background(0) + subtractive shape = black.

    fill(0.8, 0.2, 0, random())
    for i in range(100):
        r = 50 + random(100)
        oval(random(500), random(500), r, r)

    # When you're done, reset to the default NodeBox blend mode,
    # which enables alpha transparency for images.
    glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA)

    
canvas.size = 500, 500
canvas.run(draw)
