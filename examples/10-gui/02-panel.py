# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *
from nodebox.gui import *

# A panel is a container for other GUI controls.
# Controls can be added to the panel, 
# and organized by setting the controls' x and y properties
# (since all controls inherit from Layer, they all have the same properties as a layer).
panel = Panel("Example", width=200, height=200, fixed=False, modal=False)

# Alternatively, a layout manager can be added to a panel.
# A layout manager is itself a group of controls.
# By calling Layout.apply(), the manager will take care of arranging its controls.
# A simple layout manager is "Rows" layout, in which each control is drawn on a new row.
# A caption can be defined for each control in the Rows layout,
# it will be placed to the left of each control.
layout = Rows()
layout.extend([
    Field(value="hello world", hint="text", id="text"),
    ("size",  Slider(default=1.0, min=0.0, max=2.0, steps=100, id="size")),
    ("alpha", Slider(default=1.0, min=0.0, max=1.0, steps=100, id="alpha")),
    ("show?", Flag(default=True, id="show"))
])

# The panel will automatically call Layout.apply() when the layout is added.
panel.append(layout)

# With Panel.pack(), the size of the panel is condensed as much as possible.
panel.pack()

# Panel inherits from Layer,
# so we append it to the canvas just as we do with a layer:
canvas.append(panel)

def draw(canvas):

    canvas.clear()
    
    # In this simple example,
    # we link the values from the controls in the panel to a displayed text.
    # Controls with an id are available as properties of the panel
    # (e.g. a control with id "slider" can be retrieved as Panel.slider).
    # Most controls have a Control.value property that retrieves the current value:
    if panel.show.value == True:
        font("Droid Serif")
        fontsize(50 * panel.size.value)
        fill(0, panel.alpha.value)
        text(panel.text.value, 50, 250)

canvas.size = 500, 500
canvas.run(draw)

# Note:
# We named one of the sliders "alpha" instead of "opacity",
# which would be a more comprehensible id, but which is already taken
# because there is a Panel.opacity property (inherited from Layer).
# In reality, it is much better to choose less ambiguous id's,
# such as "field1_text" or "slider2_opacity".
