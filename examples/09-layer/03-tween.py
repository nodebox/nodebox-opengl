# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# This example demonstrates motion tweening and prototype-based inheritance on layers.

# Motion tweening is easy: set the Layer.duration parameter to the amount of seconds
# it should take for transformations to take effect.

# Prototype-based inheritance is used because we were lazy.
# Normally, you create a subclass of layer, give it extra properties (image, color, ...)
# and override its draw() method. The only problem (aside from the repetitive work)
# is Layer.copy(). This creates a copy of the layer with all of its properties,
# but NOT the custom properties we added in a subclass. So we'd have to implement
# our own copy() method for each custom layer that we want to reuse.

# Layers can also use dynamic, prototype-based inheritance, where layers are "inherited"
# instead of subclassed. Custom properties and methods can be set with Layer.set_property()
# and Layer.set_method(). This ensures that they will be copied correctly.

# Create a layer that draws an image, and has the same dimensions as the image.
# It transforms from the center, and it will take one second for transformations to complete.
creature = Layer.from_image("creature.png", x=250, y=250, origin=CENTER, duration=1.0)

# Add a new on_mouse_press handler to the prototype:
def whirl(layer, mouse):
    layer.x += random(-100, 100)
    layer.y += random(-100, 100)
    layer.scaling += random(-0.2, 0.2)
    layer.rotation += random(-360, 360)
    layer.opacity = random(0.5, 1.0)
    
creature.set_method(whirl, "on_mouse_press")

# Add a number of copies to the canvas.
for i in range(4):
    canvas.append(creature.copy())

canvas.size = 500, 500
canvas.run()
