import bezier
import context
import geometry
import physics
import shader

from noise   import noise
from context import *

physics.line    = context.line
physics.ellipse = context.ellipse
physics.Text    = context.Text

#-----------------------------------------------------------------------------------------------------
# Expose the canvas and some common canvas properties on global level.
# Some magic constants from NodeBox are commands here:
# - WIDTH  => width()
# - HEIGHT => height()
# - FRAME  => frame()

canvas = Canvas()

def size(width=None, height=None):
    if width is not None:
        canvas.width = width
    if height is not None:
        canvas.height = height
    return canvas.size

def speed(fps=None):
    if fps is not None:
        canvas.fps = fps
    return canvas.fps

def frame():
    return canvas.frame
    
def clear():
    canvas.clear()