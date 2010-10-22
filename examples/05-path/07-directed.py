# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0,os.path.join("..",".."))

from nodebox.graphics import *

# This example demonstrated how to use the directed() command
# to fit text to a path (thanks to Karsten Wolf).

# Create a Text object for each character.
txt = "NodeBox for OpenGL"
chars = [Text(ch, fontname="Droid Sans Mono") for ch in txt]
  
def draw(canvas):
    
    background(1)
    
    # Create a path where the mouse position controls the curve.
    dx = canvas.mouse.x
    dy = canvas.mouse.y
    path = BezierPath()
    path.moveto(100, 250)
    path.curveto(200, 250, dx, dy, 400, 250)

    # Calculate points on the path and draw a character at each points.
    # The directed() commands yields (angle, pt)-tuples.
    # The angle can be used to rotate each character along the path curvature.
    points = path.points(amount=len(chars), start=0.05, end=0.95)
    for i, (angle, pt) in enumerate(directed(points)):
        push()
        translate(pt.x, pt.y)
        rotate(angle)
        text(chars[i], x=-textwidth(chars[i])/2)
        pop()
    
    drawpath(path, fill=None, stroke=(0,0,0,0.5))
    line(path[-1].x, path[-1].y, dx, dy, stroke=(0,0,0,0.1))

canvas.fps  = 30      
canvas.size = 500, 500
canvas.run(draw)
