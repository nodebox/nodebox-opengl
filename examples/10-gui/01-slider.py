# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *
from nodebox.graphics.geometry import coordinates
from nodebox.gui import Slider

# The nodebox.gui module provides simple visual controls, such as Slider, Button, CheckBox and Field.
# Each control inherits from a Control class, which in turn inherits from Layer.
# This means that to display a control, we append it to the canvas just like a layer,
# and we set its x and y properties to define its location on the canvas.

slider1 = Slider(default=45.0, min=10.0, max=90.0, steps=9)
slider1.x = 180
slider1.y = 120

slider2 = Slider(default=3.0, min=2.0, max=10.0, steps=100)
slider2.x = 180
slider2.y = 100

canvas.append(slider1)
canvas.append(slider2)

# Now we need something to play with.
# We'll use the two sliders to control the motion of a few "snakes".
# Each snake is essentially a list of positions, 
# which we draw as ellipse segments connected by lines.

class Snake:
    
    def __init__(self, x, y):
        self.x      = x           # Current horizontal position.
        self.y      = y           # Current vertical position.
        self.radius = 2           # Current segment size.
        self.angle  = random(360) # Current heading.
        self.step   = 1           # Next segment, add or subtract step from heading.
        self.trail  = []          # List of previous (x, y, radius)-tuples.
    
    def update(self):
        # Calculate new position from the current heading and segment size.
        # The coordinates() function takes a point, a distance and an angle,
        # and returns the point at the given angle and distance from the given point.
        x, y = coordinates(self.x, self.y, self.radius*3, self.angle)
        self.angle += choice((-self.step, self.step))
        # Confine the snake to the visible area.
        self.x = max(0, min(x, 500))
        self.y = max(0, min(y, 500))
        # Add the new segment. 
        # Snake can have 200 segments maximum.
        self.trail.insert(0, (x, y, self.radius))
        self.trail = self.trail[:200]
    
    def draw(self):
        for i, (x, y, r) in enumerate(self.trail):
            if i > 0:
                line(x, y, self.trail[i-1][0], self.trail[i-1][1])
            ellipse(x, y, r*2, r*2)
        
snakes = [Snake(250, 250) for i in range(5)]

def draw(canvas):
    
    canvas.clear()

    v1 = slider1.value # Value from first slider controls snakes' heading.
    v2 = slider2.value # Value from second slider controls snakes' segment size.

    fill(0.1, 0.1, 0, 0.25)
    stroke(0.1, 0.1, 0, 0.5)
    for snake in snakes:
        snake.step = v1
        snake.radius = v2
        snake.update()
        snake.draw()

canvas.size = 500, 500
canvas.run(draw)