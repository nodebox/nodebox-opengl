# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# Here is the "Hypnoval", a classic example in NodeBox for Mac OS X.
# It uses the canvas.frame counter to create variation in each frame.
# Math functions sin() and cos() are used to create fluid motion.
# Sine and cosine describe smooth repetitive oscillation between -1 and 1:
# sin(0)=0, sin(pi/2)=1, sin(-pi/2)=-1
# cos(0)=1, cos(pi/2)=0, cos(pi)=-1
# Values near 0 occur more frequently than those near 1 (i.e. "faster" near 1).

def draw(canvas):
    
    canvas.clear()
    
    # A counter based on the current frame:
    i = canvas.frame * 0.1
    
    # We also use an internal counter that modifies individual ellipses.
    step = 0.0

    # The grid() function yields (x,y)-coordinates in a grid.
    # In this case the grid is 10 by 10 with 45 pixels spacing.
    for x, y in grid(10, 10, 45, 45):
        x += 50 # Displace a little bit from the left edge.
        y += 50 # Displace a little bit from the bottom edge.
        
        # Draw the ellipse:
        fill(0.15, 0.25 - 0.2*sin(i+step), 0.75, 0.5)
        ellipse(
            x + sin(i+step) * 10.0, # Play around with the numbers!
            y + cos(i+step) * 20.0, width=50, height=50)
            
        # Increase the step so that each ellipse looks different.
        step += 0.05


canvas.size = 500, 500
canvas.run(draw)