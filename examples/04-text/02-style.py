# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

txt = Text("So long!\nThanks for all the fish.", 
          font = "Droid Serif", 
      fontsize = 20, 
    fontweight = BOLD,
    lineheight = 1.2,
          fill = color(0.25))

# Text.style() can be used to style individual characters in the text.
# It takes a start index, a stop index, and optional styling parameters:
txt.style(9, len(txt), fontsize=txt.fontsize/2, fontweight=NORMAL)

def draw(canvas):
    
    canvas.clear()

    x = (canvas.width - textwidth(txt)) / 2
    y = 250
    text(txt, x, y)
    
canvas.size = 500, 500
canvas.run(draw)