# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# The BezierPath object handles complex vector shapes made up of curves and lines.
# As with images and text, it is a good idea to create the path once, outside the draw loop.
# OpenGL has to perform an operation called "tessellation" (dividing the shape into triangles)
# before it can be drawn. Furthermore, curves have to be divided into a group 
# of small straight lines before they can be drawn. These operations take time.
# BezierPath will perform them once and then cache the results,
# therefore creating a new path each frame slows down your app.

# Create a leaf shape.
# BezierPath has moveto(x,y), lineto(x,y), curveto(x1, y1, x2, y2, x3, y3) and close() methods.
# For curveto(), (x1,y1) describes the direction in which the curve from this point starts,
# and (x2,y2) describes the direction in which it ends in point (x,y).
# In this case, moveto() positions the current point at origin (0,0).
# Then we draw a curve upwards, bulging out to the right and ending in a spike.
# Then we draw a curve back to the origin, starting in a spike and bulging out to the left.
leaf = BezierPath()
leaf.moveto(0, 0)
leaf.curveto(50, 50, 0, 150, 0, 200)
leaf.curveto(0, 150, -50, 50, 0, 0)

# The resulting path can be passed to drawpath() to render it to the canvas.
# Note: just as in the classic NodeBox for Mac OS X, paths can also be constructed
# with beginpath(). The commands below create exactlye the same leaf shape as above:
#  beginpath(0, 0)
#  curveto(50, 50, 0, 150, 0, 200)
#  curveto(0, 150, -50, 50, 0, 0)
#  p = endpath(draw=False)

def draw(canvas):

    canvas.clear()
    
    fill(0.25, 0.15, 0.75, 0.25) # Transparent purple/blue.
    stroke(0, 0.25) # High transparency makes the stroke look thinner.
    strokewidth(1)
    
    translate(250, 250) # Origin in the center of the canvas.
    for i in range(40):
        rotate(9)
        drawpath(leaf)
	
canvas.size = 500, 500
canvas.run(draw)