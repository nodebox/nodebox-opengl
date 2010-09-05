# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# The classic NodeBox for Mac OS X has interesting path mathematics functionality.
# This functionality is also present in NodeBox for OpenGL.
# For example: we can calculate arbitrary points on a path, 
# insert new points, construct a smooth BezierPath from a list of points, etc.

# What we want to do in this example,
# is place copies of a leaf (see the previous example) along a path (or stem).
# This is achieved by calculating points along a curve and retrieving their "direction".

# Create a leaf shape.
leaf = BezierPath()
leaf.moveto(0, 0)
leaf.curveto(50, 50, 0, 150, 0, 200)
leaf.curveto(0, 150, -50, 50, 0, 0)

# Create the stem.
stem = BezierPath()
stem.moveto(150, 100)
stem.curveto(50, 400, 450, 400, 350, 100)

def draw(canvas):
    
    canvas.clear()

    nofill()
    stroke(0, 0.25)
    strokewidth(1)
    
    drawpath(stem)

    fill(0.25, 0.15, 0.75, 0.25)

    # The BezierPath.points() method yields points evenly distributed along the path.
    # The directed() iterator yields (angle, point)-tuples
    # for each point in a BezierPath(), BezierPath.points() list, or list of Point objects.
    # - The angle represents the direction into which the curve is bending.
    # - The line drawn in this direction is known as the curve's tangent.
    # This is useful in many ways, for example: to fit text to a path,
    # or to place elements (e.g. leaves, moving creatures) along a curved trajectory.
    for angle, pt in directed(stem.points(50)):
        push()
        translate(pt.x, pt.y) # Position the origin point at the current point.
        scale(0.5)            # Scale it down.
        rotate(angle)         # Rotate in the point's direction (you may need to add 90, 180, ...)
        drawpath(leaf)        # Draw the leaf.
        rotate(90)            # Indicate the normal (i.e. the line perpendicular to the tangent)
        line(0, 0, 300, 0, strokestyle=DASHED)
        pop()                 # Reset origin point, scale and rotation.
            
canvas.size = 500, 500
canvas.run(draw)

