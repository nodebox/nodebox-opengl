# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# The render() command executes a function with drawing commands 
# in an offscreen (i.e. hidden) canvas and returns an Image object.
# This is useful if you want to apply filters to text, ellipses, etc.
def hello():
    fill(1, 0, 0, 0.5) # Transparent red.
    ellipse(120, 120, 200, 200)
    fill(0, 1, 0, 0.5) # Transparent green.
    ellipse(170, 120, 200, 200)
    fill(0, 0, 1, 0.5) # Transparent blue. 
    ellipse(145, 160, 200, 200)
    fill(0)
    font("Droid Serif")
    text("hello", x=0, y=90, fontsize=70, width=300, align=CENTER)

# We call this a "procedural" image, because it is entirely created in code.
# Procedural images can be useful in many ways:
# - applying effects to text, 
# - caching a complex composition that is not frequently updated (for speed),
# - creating on-the-fly textures or shapes that are different every time,
# - using NodeBox from the command line without opening an application window.
img = render(function=hello, width=300, height=300)

# Note that we make the width and height of the offscreen canvas
# a little bit larger than the actual composition.
# This creates a transparent border, so effects don't get cut off
# at the edge of the rendered image.

# Images can be saved to file, even without starting canvas.run().
# To try it out, uncomment the following line:
#img.save("hello.png")

def draw(canvas):
    
    canvas.clear()

    # Apply a blur filter to the procedural image and draw it.
    image(blur(img, scale=canvas.mouse.relative_x), 20, 100)
    
    # Compare to the same shapes drawn directly to the canvas.
    # You may notice that the rendered image has jagged edges...
    # For now, there is nothing to be done about that - a soft blur can help.
    translate(300,100)
    fill(1, 0, 0, 0.5)
    ellipse(120, 120, 200, 200)
    fill(0, 1, 0, 0.5)
    ellipse(170, 120, 200, 200)
    fill(0, 0, 1, 0.5) 
    ellipse(145, 160, 200, 200)
    
# Start the application:
canvas.fps  = 60
canvas.size = 600, 500
canvas.run(draw)
