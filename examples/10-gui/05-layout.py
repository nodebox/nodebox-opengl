# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *
from nodebox.gui import *

# Comparison between Rows and Row containers.
# Both are subclasses of Layout.

# Panel 1
# Controls in a Rows layout are drawn below each other.
# Rows.width defines the width of all controls (individual width is ignored).
# Note how the second Field has a height and wrap=True, 
# which makes it a multi-line field with text wrapping.
panel1 = Panel("Panel 1", x=30, y=350)
panel1.append(
    Rows([
        Field(value="", hint="subject"),
        Field(value="", hint="message", height=70, id="field_msg1", wrap=True),
        Button("Send"),
    ], width=200)
)
panel1.pack()

# Panel 2
# Controls in a Row layout are drawn next to each other.
# Row.width defines the width of all controls (individual width is ignored).
# This means that each column has the same width.
# Note the align=TOP, which vertically aligns each column at the top (default is CENTER).
panel2 = Panel("Panel 2", x=30, y=200)
panel2.append(
    Row([
        Field(value="", hint="message", height=70, id="field_msg2", wrap=True),
        Button("Send", width=400),
    ], width=200, align=TOP)
)
panel2.pack()

# Panel 3
# If you need columns of a different width, put a Layout in a column,
# in other words a Row or Rows nested inside a Row or Rows.
# Then put your controls in the nested layout, 
# the layout's width will override the column width setting.
panel3 = Panel("Panel 3", x=30, y=30)
panel3.append(
    Row([ # Field will be 200 wide, the Row column width setting.
        Field(value="", hint="message", height=70, id="field_msg2", wrap=True),
        ("Actions:", Rows([
            Button("Send"), # However, buttons will be 100 wide,
            Button("Save")  # because their Rows parent says so.
        ], width=100))
    ], width=200, align=TOP)
)
panel3.pack()

# Panel 4
# Without layouts, you are free to draw controls wherever you want in a panel.
# Panel.pack() will make sure that the panel fits snuggly around the controls.
# In this case, we place a button on the panel, with a field above it (hence y=40).
# The field has its own dimensions (width=300 and height=50).
panel4 = Panel("Panel 4", x=400, y=30)
panel4.extend([
    Field(value="", hint="message", y=40, width=300, height=50, id="field_msg3", wrap=True, reserved=[]),
    Button("Send")
])
panel4.pack()

# Note the reserved=[] with the field.
# By default, fields have ENTER and TAB keys reserved:
# enter fires Field.on_action(), tab moves away from the field.
# By clearing the reserved list we can type enter and tab inside the field.

# Panel 5
# If you don't pack the panel, you have to set its width and height manually,
# as well as the position of all controls:
panel5 = Panel("Panel 5", x=500, y=200, width=200, height=150)
panel5.extend([
    Field(value="", hint="message", x=10, y=60, width=180, height=50, id="field_msg3", wrap=True),
    Button("Send", x=10, y=20, width=180)
])

def draw(canvas):
    canvas.clear()

canvas.append(panel1)
canvas.append(panel2)
canvas.append(panel3)
canvas.append(panel4)
canvas.append(panel5)
canvas.size = 800, 600
canvas.run(draw)