# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *
from nodebox.sound import PD, LOCALHOST, IN, OUT

# This script demonstrates how to simultaneously receive from and send to Pd.
# We need two communication ports. By default, NodeBox receives on port 44000 (IN),
# so Pd should send from port 44000. NodeBox sends on port 44001 (OUT),
# so Pd should receive om port 44001.

# With start=False, the patch will not be loaded automatically in the background.
# This means that you must open Pd manually and load the patch.
# This is necessary, because we'll use the Pd GUI to control the NodeBox animation.
pd = PD("02-in-out.pd", start=False)
    
def draw(canvas):
    canvas.clear()
    # As you can see in the Pd patch, it broadcasts three values,
    # which we use to control the size, color and rotation of a rectangle.
    # You may have to drag the numbers up or down in Pd in order for the rectangle to appear.
    data = pd.get("/output", host=LOCALHOST, port=IN)
    if data:
        size, color, angle = data
        translate(250, 250)
        rotate(angle)
        fill(0, color/255.0, 0)
        rect(-size/2, -size/2, size, size)
    # As a test, send the mouse position to Pd.
    # If you click the NodeBox application window and move the mouse around,
    # you'll see the (x,y) position printed in the main Pd window.
    pd.send((canvas.mouse.x, canvas.mouse.y), "/input", host=LOCALHOST, port=OUT)

# We can send data to Pd to generate sound interactively.
# We can receive data from Pd to create an animation that responds to sound.

def stop(canvas):
    pd.stop()

canvas.size = 500, 500
canvas.run(draw, stop=stop)

