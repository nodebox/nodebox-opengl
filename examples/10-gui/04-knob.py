# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *
from nodebox.gui import *

# This example demonstrates the knob GUI control, 
# and how different layout managers can be nested.
# Knobs look nice when placed next to each other.
# The "Row" layout can be used to achieve this.
# It arranges all of its controls horizontally, with their captions on top.
# The Row layout can then be nested in a Rows layout (or vice versa).
# This allows you to build many different interface grids.
panel = Panel("Example", width=300, height=200, fixed=False, modal=False)
panel.append(Rows(
    [("text",Field(value="hello world", hint="text", id="field_text")),
     (    "size", Slider(default=1.0, min=0.0, max=2.0, steps=100, id="slider_size")),
     ( "opacity", Slider(default=1.0, min=0.0, max=1.0, steps=100, id="slider_opacity")),
     (   "color", Row([("R", Knob(id="knob_r")),
                       ("G", Knob(id="knob_g")),
                       ("B", Knob(id="knob_b"))
                      ]))]))
panel.pack()
canvas.append(panel)

def draw(canvas):
    
    canvas.clear()

    font("Droid Serif")
    fontsize(50 * panel.slider_size.value)
    fill(panel.knob_r.relative, # Knob.value is between 0-360.
         panel.knob_g.relative, # Knob.relative between 0.0-1.0.
         panel.knob_b.relative,
         panel.slider_opacity.value)
    text(panel.field_text.value, 20, 200)

canvas.size = 500, 500
canvas.run(draw)