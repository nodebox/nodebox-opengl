# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *
from nodebox.gui import *

# This is the same example as the previous, but with a button added to the panel.
# All controls have a Control.on_action() event that fires when the user
# interacts with the control (for a slider: dragging the slider, for a flag:
# toggling the flag, for a field: hitting enter, for a button: clicking it).

def reset_panel(button):
    # A simple action which we will link to the button.
    # It fires when the button is pressed.
    panel = button.parent.parent # First parent is the Rows layout, parent of the layout is the panel.
    panel.field_text.reset()
    panel.slider_size.reset()
    panel.slider_opacity.reset()
    panel.show.reset()

panel = Panel("Example", width=200, height=200, fixed=False, modal=False)
panel.append(Rows(
    [Field(value="hello world", hint="text", id="field_text"),
     (    "size", Slider(default=1.0, min=0.0, max=2.0, steps=100, id="slider_size")),
     ( "opacity", Slider(default=1.0, min=0.0, max=1.0, steps=100, id="slider_opacity")),
     (   "show?", Flag(default=True, id="show")),
     Button("Reset", action=reset_panel), # Register our function as the button's action.
]))
panel.pack()
canvas.append(panel)

def draw(canvas):
    
    canvas.clear()

    if panel.show.value == True:
        font("Droid Serif")
        fontsize(50 * panel.slider_size.value)
        fill(0, panel.slider_opacity.value)
        text(panel.field_text.value, 50, 250)

canvas.size = 500, 500
canvas.run(draw)