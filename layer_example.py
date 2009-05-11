from nodebox.graphics import context
from time import time
import pyglet
from pyglet.gl import *

from nodebox.graphics import Layer, Canvas, canvas, gradient, run, size, rect, color, background, random, rotate
size(700, 700)
WIDTH, HEIGHT = 700, 700

class RotatedObject(Layer):
    
    def __init__(self, *args, **kwargs):
        super(RotatedObject, self).__init__(*args, **kwargs)
        self.origin = (1.0, 0.5)
        self.rotation = 1.0
        
    def update(self):
        if self.done:
            self.rotation = random(-360.0, 360.0)

    def draw(self):
        rect(0, 0, self.width, self.height, fill=color(1.0, 0.0, 0.0))

canvas.append(RotatedObject(400, 400, 100, 100))
canvas.run()
