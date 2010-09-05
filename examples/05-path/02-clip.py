# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# Here, the leaf shape from the previous example is reused,
# but instead of simply coloring it with blue, we give it a nice gradient touch.
# Such effects - if your application has room to pull it off, add depth and realism.
# We'll use a clipping mask to achieve this.

# Create a leaf shape.
leaf = BezierPath()
leaf.moveto(0, 0)
leaf.curveto(50, 50, 0, 150, 0, 200)
leaf.curveto(0, 150, -50, 50, 0, 0)

def draw(canvas):

    canvas.clear()
    
    translate(250, 250)
    for i in range(12):
        rotate(30)
        # Instead of drawing the path directly, we use it as a clipping mask.
        # All shapes drawn between beginclip() and endclip() that fall
        # outside the clipping path are hidden.
        # Inside we use a colorplane to draw a gradient;
        # comment out beginclip() and endclip() to observe what happens.
        beginclip(leaf)
        colorplane(-75, 0, 150, 200,
            color(0.25, 0.15, 0.75, 0.65), # Gradient top color.
            color(0.15, 0.45, 0.95, 0.15)  # Gradient bottom color.
        )
        endclip()
        
        # For a sublte finishing touch,
        # we could also add the leaf stroke back on top:
        drawpath(leaf, stroke=(0,0,0,0.25), strokewidth=1, fill=None)
	
canvas.size = 500, 500
canvas.run(draw)