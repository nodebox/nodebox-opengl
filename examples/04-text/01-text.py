# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# In the classic NodeBox for Mac OS X, text can easily be drawn with text(), font(), fontsize().
# This is possible here as well, but it is much faster to prepare the text beforehand:
txt = Text("hello, world", font="Droid Serif", fontsize=20, fontweight=BOLD)

# The less changes you make to the text, the faster it is drawn.

# A Text object has many different typographical parameters:
# - font: the name of the font to use (e.g. "Droid Sans", "Helvetica", ...),
# - fontsize: the fontsize in points,
# - fontweight: NORMAL, BOLD, ITALIC or a (BOLD, ITALIC)-tuple,
# - lineheight: line spacing, 1.0 by default,
# - align: LEFT, RIGHT or CENTER,
# - fill: a Color object that sets the color of the text.

def draw(canvas):
    
    canvas.clear()
    
    # Center the text horizontally.
    # Vertically, the y position is the baseline of the text.
    x = (canvas.width - textwidth(txt)) / 2
    y = 250
    text(txt, x, y)
    
canvas.size = 500, 500
canvas.run(draw)