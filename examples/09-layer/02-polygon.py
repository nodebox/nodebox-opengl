# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# Since a layer is a rectangular area, all mouse events are also triggered in a rectangle.
# This can be a bit clumsy in some situations. 
# For example: a game environment in which objects light up when the mouse moves over them. 
# Not every object fits in a rectangle - so there will be areas that light up the object
# even if the mouse is not over the actual object.
# If you want to do "hit testing" on irregular areas, you can use BezierPath.contains(x, y).

# BezierPath.contains() returns True when the given position is inside the path.
# However, on the canvas, the path might have been rotated and scaled.
# It may be part of a function, loop, and subject to several intermediary scale() and rotate() calls,
# so that its position and shape on the canvas has become entirely different.
# To check whether a position falls inside a transformed path, we first need to *apply* the transformations.
# This can be done with a Transform object from the geometry module,
# which is like a personal transform state:
#
# from nodebox.geometry import Transform
# path = star(x=50, y=50, points=7, outer=100, draw=False)
# tf = Transform()
# tf.translate(100, 0)
# tf.rotate(45)
# path = tf.transform_path(path)
#
# This effectively modifies the position of all points in the path,
# so that they are translated 100 pixels horizontally and then rotated 45 degrees.

class DraggablePolygon(Layer):
    
    def __init__(self, *args, **kwargs):
        Layer.__init__(self, *args, **kwargs)
        # The actual shape of the layer is a star.
        # Events should only be triggered when inside the star.
        self.path = star(x=self.width/2, y=self.height/2, points=7, outer=100, draw=False)
        # The layer.transform property is a Transform object
        # that contains all the transformations the layer has been subjected to.
        # Each time the layer is modified, we'll modify the path too.
        self.area = self.transform.transform_path(self.path)
        self.over = False # True when mouse is over the star.
    
    def draw(self):
        if self.over:
            clr = color(0.0, 0.5, 0.75, 0.75)
        else:
            clr = color(0.0, 0.5, 0.75, 0.5)
        drawpath(self.path, fill=clr, stroke=clr)
    
    def on_mouse_motion(self, mouse):
        # Here's the trick.
        # When the mouse moves inside the layer's rectangle,
        # we do an additional check to see if it is also over the transformed path:
        if self.area.contains(mouse.x, mouse.y):
            mouse.cursor = HAND
            self.over = True
        else:
            mouse.cursor = DEFAULT
            self.over = False
    
    def on_mouse_drag(self, mouse):
        # When inside the transformed path, dragging is enabled.
        # The changes to the layer are also applied to the path.
        if self.over:
            self.scale(1 + 0.005 * mouse.dy)
            self.rotate(mouse.vx)
            self.area = self.transform.transform_path(self.path)

p = DraggablePolygon(x=250, y=250, width=200, height=200, origin=(0.5,0.5))

canvas.append(p)
canvas.size = 500, 500
canvas.run()
