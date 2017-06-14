from nodeboxgl.graphics import *
from math import sin, cos

# The Peter De Jong attractor feeds its previous value back into the equation,
# creating a scatter of points that generates strange, attractive patterns.
# The function's return value is a Python iterator - an implicit list of (x,y)-values.
# All of the iterator's values can be retrieved one by one in a loop,
# or you can move to the next value with iterator.next().
def peter_de_jong_attractor(a, b, c, d, n=100000, scale=100):
    x0, y0 = 0.0, 0.0
    for i in range(n):
        x1 = sin(a*y0) - cos(b*x0)
        y1 = sin(c*x0) - cos(d*y0)
        x0 = x1
        y0 = y1
        yield (x1*scale, y1*scale)
        
# Classic example from http://local.wasp.uwa.edu.au/~pbourke/fractals/peterdejong/
# Play around with the numbers to produce different patterns.
a = peter_de_jong_attractor(1.4, -2.3, 2.4, -2.1, n=5000000, scale=150)

def draw(canvas):
    
    # The trick is not to clear the canvas each frame.
    # Instead, we only draw a background in the first frame,
    # and then gradually build up the composition with the next points each frame.
    if canvas.frame == 1:
        background(1)
    
    # Translate the canvas origin point to the center.
    # The attractor can yield negative (x,y)-values,
    # so if we leave the origin point in the bottom left,
    # part of the pattern will fall outside the drawing area.
    translate(canvas.width/2, canvas.height/2)

    # Note how the fill color has a very low alpha (i.e. high transparency).
    # This makes the pattern more fine-grained,
    # as many transparent points will need to overlap to form a thicker line.      
    fill(0, 0.1)
    
    try:
        for i in range(1000):
            # Get the next x and y coordinates in the attractor.
            # Draw a pixel at the current x and y coordinates.
            x, y = a.next()
            rect(x, y, 1, 1)
    except StopIteration:
        pass

canvas.size = 700, 700
canvas.run(draw)
