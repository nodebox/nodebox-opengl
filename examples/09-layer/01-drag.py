# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# In the previous examples, drawing occurs directly to the canvas.
# It is also possible to draw into different layers, 
# and then transform / animate the layers individually.
# The Layer class introduces a lot of useful functionality:
# - layers can receive events from the mouse,
# - layers have an origin point (e.g. "center") from which transformations originate,
# - layers have methods such as Layer.rotate() and Layer.scale(),
# - layers can enable motion tweening (i.e. smooth, automatic transititions).

# A Layer has its personal Layer.draw() method that contains drawing commands.
# In this example, we create a subclass of Layer to display a colored, draggable rectangle:

class DraggableRect(Layer):
    
    def __init__(self, *args, **kwargs):
        # A Layer with an extra "clr" property.
        Layer.__init__(self, *args, **kwargs)
        self.clr = Color(0, 0.75)
    
    def draw(self):
        rect(0, 0, self.width, self.height, fill=self.clr, stroke=self.clr)
    
    def on_mouse_enter(self, mouse):
        # When the mouse hovers over the rectangle, highlight it.
        mouse.cursor = HAND
        self.clr.a = 0.75
    
    def on_mouse_leave(self, mouse):
        # Reset the mouse cursor when the mouse exits the rectangle.
        mouse.cursor = DEFAULT
        self.clr.a = 0.5
    
    def on_mouse_drag(self, mouse):
        # When the rectangle is dragged, transform it.
        # Its scale increases as the mouse is moved up.
        # Its angle increases as the mouse is moved left or right.
        self.scale(1 + 0.005 * mouse.dy)
        self.rotate(mouse.dx)

# The layer's origin defines the origin point for the layer's placement,
# its rotation and scale. If it is (0.5, 0.5), this means the layer will transform
# from its center (i.e. 50% width and 50% height). If you supply integers,
# the values will be interpreted as an absolute offset from the layer's bottom-left corner.
r1 = DraggableRect(x=200, y=200, width=200, height=200, origin=(0.5,0.5), name="blue1")
r1.clr = color(0.0, 0.5, 0.75, 0.5)

r2 = DraggableRect(x=250, y=250, width=200, height=200, origin=(0.5,0.5), name="blue2")
r2.clr = color(0.0, 0.5, 0.75, 0.5)

r3 = DraggableRect(x=300, y=300, width=200, height=200, origin=(0.5,0.5), name="purple1")
r3.clr = color(0.25, 0.15, 0.75, 0.5)

# We'll attach a layer as a child to layer r3.
# Child layers are very handy because they transform together with their parent.
# For example, if the parent layer rotates, all of its children rotate as well.
# However, all of the layers can still receive separate mouse and keyboard events.
# You can use this to (for example) create a flying creature that responds differently
# when the mouse touches its wings or its head - but where all the body parts stick together.

# Position the child's center at (100,100) relative from the parent's layer origin:
r4 = DraggableRect(x=100, y=100, width=100, height=100, origin=(0.5,0.5), name="purple2")
r4.clr = color(0.25, 0.15, 0.75, 0.5)
r3.append(r4)

# Even more nested child layers:
#r5 = DraggableRect(x=50, y=50, width=50, height=50, origin=(0.5,0.5), name="pink1")
#r5.clr = color(1.00, 0.15, 0.75, 0.5)
#r4.append(r5)

# The canvas is essentially a list of layers, just as an image in Photoshop is a list of layers.
# Appending a layer to the canvas ensures that it gets drawn each frame,
# that it receives mouse and keyboard events, and that its motion tweening is updated.
canvas.append(r1)
canvas.append(r2)
canvas.append(r3)

def draw(canvas):
    # There is nothing to draw here;
    # all the drawing occurs in the separate layers.
    canvas.clear()
    
canvas.size = 500, 500
canvas.run(draw)

# Note: if you have layers that do not need to receive events,
# set Layer.enabled = False; this saves some time doing expensive matrix operations.