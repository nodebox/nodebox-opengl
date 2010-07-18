# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.append(os.path.join("..",".."))

from nodebox.graphics import *

# Often, you may need groups of shapes that you can transform as a whole.
# For example: a planet that has moons rotating around it.
# The planet+moons is a group that as a whole rotates around a sun.

txt = Text("moon")

def draw(canvas):
    
    canvas.clear()
    
    stroke(0, 0.2)
    
    # Put the origin point in the center of the canvas.
    translate(canvas.width/2, canvas.height/2)
    ellipse(0, 0, 10, 10)
    text("sun", 10, 0)

    n = 3
    for i in range(n):
        
        # The push() and pop() commands can be used to create a branch in the transform state.
        # Once push() is called, transformations are in effect until pop() is called, 
        # at which point the transformation state resets to the way it was before push().
        # Each planet acts as a local origin for its orbitting moon.
        push()
        rotate(canvas.frame + i*360.0/n) # Rotate around sun.
        line(0, 0, 120, 0)               # Draw a (rotated) line with length 120.
        translate(120, 0)                # Move the origin to the end of the (rotated) line.
        ellipse(0, 0, 5, 5)              # Draw the planet at the end of the (rotated) line.
        text("planet", 10, 0)
        rotate(canvas.frame * 6)         # Increase rotation.
        line(0, 0, 30, 0)                # Draw a line with length 30 from the planet.
        text("moon", 32, 0)
        pop()                            # Move the origin back to the sun. Undo rotation.

canvas.size = 500, 500
canvas.run(draw)