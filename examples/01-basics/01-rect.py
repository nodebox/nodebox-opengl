# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

# Import the drawing commands from the NodeBox module.
from nodebox.graphics import *
# This includes:
# - drawing primitives such as line(), rect(), ellipse(), triangle(),
# - color commands such as fill(), stroke(), strokewidth(),
# - transform commands such as translate(), rotate(), scale(), push() and pop(),
# - bezier commands such as beginpath(), endpath(), moveto(), lineto(), curveto(), drawpath(),
# - image commands such as image() and crop(),
# - image filters such as blur(), colorize(), 
# - text commands such as text(), font(), fontsize(),
# - foundation classes such as Color, BezierPath, Image, Text, Layer and Canvas.

# The canvas will update several times per second.
# The idea is to write a draw() function that contains a combination of drawing commands.
# The draw() function is attached to the canvas so that its output is shown every frame.
# The canvas has a timer for the current frame and logs the position of the mouse,
# these can be used to create different animations for each frame.
def draw(canvas):

    # Clear the previous frame.
    # This does not happen by default, because interesting effects can be achieved
    # by not clearing the background (for example, see math/1-attractor.py).
    canvas.clear()
    
    # Draw a rectangle.
    # The x parameter defines the horizontal offset from the left edge of the canvas.
    # The y parameter defines the vertical offset from the bottom edge of the canvas.
    # The rectangle's height is 100 minimum, and grows when you move the mouse up.
    # Change some numbers to observe their impact.
    rect(x=100, y=10, width=300, height=max(100, canvas.mouse.y))
	
canvas.size = 500, 500 # Set the size of the canvas.
canvas.run(draw)       # Register the draw function and start the application.