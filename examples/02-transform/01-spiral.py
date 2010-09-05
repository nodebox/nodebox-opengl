# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

def draw(canvas):
    
	canvas.clear()
	
	# The origin point of the canvas is in the bottom-left corner.
	# That means if you draw a shape or image at x=0 and y=0,
	# it appears in the bottom-left corner.
	# The origin point can be moved around with the translate() command.
	# For example, here it is placed in the center of the canvas:
	translate(250, 250)
	
	# Like colors, NodeBox keeps a current transform "state".
	# All subsequent drawing commands will originate from the center.
	
	stroke(0, 0.2)
	strokewidth(1)
	
	n = 350
	for i in range(n):
	    t = float(i) / n # A counter between 0.0 and 1.0.
	    fill(0.25-t, 0.15+t, 0.75, 0.15)
	    
	    # The transform state logs the current scale.
	    # Thus, the first time when we call scale(0.99), the current scale is 99%.
	    # The second time the current scale becomes 99% of 99 = 98%, and so on.
	    # That is why each subsequent ellipse is a bit smaller than the previous one.
	    scale(0.99)
	    
	    # In the same way, rotate() calls are cumulative.
	    # The first rotate(5) sets the current angle to 5, the second 10, 15, 20, ...
	    # That is why each subsequent ellipse appears at a different angle.
	    rotate(5)
	    
	    # However, instead of drawing a lot of ellipses on top of each other,
	    # each rotated at a different angle, each ellipse is instead rotating
	    # around the origin point (which we placed in the center).
	    # This is because we draw each ellipse at x=200, so 200 pixels to the right
	    # of the origin, only "to the right" is relative to the current rotation.
	    # In the same way, "200 pixels" is relative to the current scale,
	    # so the ellipses spiral to the center.
	    ellipse(x=200, y=0, width=120, height=60)
	    
	    # The order in which transformations occur is important:
	    # translating first and scaling / rotating afterwards
	    # has a different effect than scaling / rotating first.
	
canvas.size = 500, 500
canvas.run(draw)