from nodeboxgl.graphics import *

# When you run a script, NodeBox reads the code from top to bottom, like a recipe. 
# When it encounters coloring or transformation commands, it changes the current state. 
# All subsequent elements (primitives, paths, text and images) 
# you draw then adhere to the current state.

def draw(canvas):

    canvas.clear()
    
    # The fill() command sets the current fill color.
    # This color is used for all subsequent shapes.
    # It takes four parameters: red, green, blue and opacity, ranging between 0.0 and 1.0.
    # So an opacity of 0.5 means 50% transparent.
    fill(0.0, 0.5, 0.75, 0.5) # 50 % transparent cyan (=cold greenish blue).
    
    # Some things to note:
    # 1) Both the rectangle and ellipse are drawn in the current fill color.
    # 2) The current fill is transparent, so their colors blend where they overlap.
    # 3) The rectangle is positioned from its bottom-left corner, the ellipse from the center.
    rect(50, 200, 100, 100)
    ellipse(150, 200, 100, 100)
    
    # The stroke() command sets the current outline color.
    # The strokewidth() command defines the thickness of the outline.
    # If less than four parameters are given for fill() and stroke(),
    # they are assumed to be R,G,B values (3 parameters) or grayscale + opacity (2 parameters).
    nofill()
    stroke(0.0, 0.25) # 75% transparent black.
    strokewidth(1)
    triangle(200, 200, 250, 300, 300, 200)
    
    # While rect() and ellipse() expect x, y, width, height parameters,
    # triangle() expects the coordinates of three points,
    # which are connected into a triangle.
    
    # Clear the current stroke,
    # otherwise it is still active in the next frame
    # when we start drawing the rectangle and the ellipse.
    nostroke()
    
    # You can also pass Color objects to fill() and stroke().
    # A Color object can be created with the color command.
    # It has clr.r, clr.g, clr.b, clr.a properties. 
    clr = color(0.25, 0.15, 0.75, 0.5) # 50% transparent purple/blue.
    fill(clr)
    ellipse(200, 400, 300, 300)
    
    # Display the coordinates,
    # so we can compare them with the values in the source code.
    fill(0)
    x, y = canvas.mouse.xy
    text("%s,%s"%(x,y), x, y)
	
canvas.size = 500, 500
canvas.run(draw)
