# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.append(os.path.join(".."))

from nodebox.graphics import *


from nodebox.gui import *

panel = Panel("Example", width=200, height=200)
panel.append(
    Rows(controls=[
      Field(value="hello world", hint="text"),
      ("size",    Slider(default=1.0, min=0.0, max=2.0, steps=100),
      ("opacity", Slider(default=1.0, min=0.0, max=1.0, steps=100),
      ("visible", Flag(default=True)),
      Button("Reset", action=lambda button: None)]))
panel.pack()
canvas.append(panel)
canvas.run()


def draw(canvas):
    background(1)
    translate(250, 250)
    rotate(canvas.frame)
    rect(-100, -100, 200, 200)
    
canvas.size = 500, 500
canvas.run(draw)