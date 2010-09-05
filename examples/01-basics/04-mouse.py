# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# A freehand drawing application!

# The canvas, which is passed to every draw() call,
# has a "mouse" property that logs the current mouse state.
# Ideally, you'd use event handlers such as canvas.on_mouse_press()
# but we can already play around with the mouse here:
# - canvas.mouse.x: horizontal postion of the mouse, 0 means left canvas edge,
# - canvas.mouse.y: vertical postion of the mouse, 0 means bottom canvas edge,
# - canvas.mouse.dx: horizontal offset from the previous mouse position,
# - canvas.mouse.dy: vertical offset from the previous mouse position,
# - canvas.mouse.button: mouse button pressed (LEFT | MIDDLE | RIGHT | None),
# - canvas.mouse.modifiers: a list of keyboard modifiers (CTRL | SHIFT | ALT),
# - canvas.mouse.pressed: True when a button is pressed,
# - canvas.mouse.dragged: True when the mouse is dragged.

def draw(canvas):
    
    #canvas.clear()
    if canvas.frame == 1:
        background(1)
    
    m = canvas.mouse

    strokewidth(1)
    stroke(0, 0.4)    
    if CTRL in m.modifiers:
        # If the CTRL key is held down, draw thinner lines.
        stroke(0, 0.2)
    
    if m.pressed:
        # If the mouse is pressed, draw lines.
        # This is a better way than simply drawing a dot at the current mouse position
        # (i.e. ellipse(m.x, m.y, 2, 2)), because the mouse can move faster
        # than the application can track. 
        # So each frame we draw a little line to the previous mouse position.
        line(m.x, m.y, m.x - m.dx, m.y - m.dy)

canvas.size = 500, 500
canvas.run(draw)