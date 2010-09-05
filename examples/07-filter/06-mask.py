# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# Render a radial gradient image.
# Without additional parameters, the gradient will be grayscale.
g = gradient(350, 350, type=RADIAL)

# The mask() filter covers one image with another (grayscale) image.
# You can use the grayscale() filter to make image black & white.
# The mask will hide the source image where the mask is black.
# We use the radial gradient as a mask.
# The radial gradient is white at the edges and black at the center.
# We invert it so we get black edges.
# The result is that the source image will gradually fade away at the edges.
img = Image("dendrite.png")
img = mask(img, invert(g))

# Crop the source image to the size of the mask.
# Our mask is smaller than the source image, so beyond it is still pixel data
# but we no longer need it.
img = crop(img, x=0, y=0, width=350, height=350)

def draw(canvas):
    
    #canvas.clear()
    
    # Each frame, paint a new image to the canvas.
    # Since its edges are transparent, all images blend into each other.
    # This is a useful technique if you want to create random,
    # procedural textures (e.g. tree back, rust & dirt, clouded sky, ...)
    translate(random(450), random(450))
    rotate(random(360))
    translate(-img.width/2, -img.height/2) # Rotate from image center.
    image(img)

# Start the application:
canvas.fps  = 5 # Slow framerate so we can observe what is happening.
canvas.size = 500, 500 # This is a bad idea since keyboard events 
canvas.run(draw)       # are now logged very slowly.