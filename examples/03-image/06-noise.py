# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# Create a pixels array from a solid white image:
p = Pixels(solid(200, 200, Color(1)))

# Colorize pixels with the Perlin noise() generator.
# Noise is smoother than random(), comparable to a random gradient.
# This is often used to generate terrain surface maps.

# The noise() command returns a smooth value between -1.0 and 1.0.
# The x, y, z parameters determine the coordinates in the noise landscape. 
# Since the landscape is infinite, the actual value of a coordinate doesn't matter, 
# only the distance between successive steps. 
# The smaller the difference between steps, the smoother the noise sequence. 
# Steps between 0.005 and 0.1 usually work best.
zoom = 4
for i in range(p.width):
    for j in range(p.height):
        t = noise(
            zoom * float(i) / p.width,
            zoom * float(j) / p.height
        )
        t = 0.5 + 0.5 * t # Map values from -1.0-1.0 to 0.0-1.0.
        t = int(255*t)    # Map values to 0-255.
        p[i+j*p.width] = (t,t,t,255)
        
p.update()

def draw(canvas):
    image(p, 150, 150)
    
canvas.size = 500, 500
canvas.run(draw)