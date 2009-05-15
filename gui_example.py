from nodebox.graphics import context
from time import time
import pyglet
from pyglet.gl import *

from nodebox.graphics import InteractiveLayer, Canvas, Color, \
    canvas, colorplane, run, size, rect, color, background, random, rotate, text

from nodebox.gui import Label, Button, Slider

size(700, 700)
WIDTH, HEIGHT = 700, 700

class EditableObject(InteractiveLayer):
    
    def __init__(self, **kwargs):
        super(EditableObject, self).__init__(**kwargs)
        self.r = 1.0
        self.g = 0.0
        self.b = 0.0
        self.relative_origin = (0.5,0.5)
        self.duration = 0.2

    def draw(self):
        rect(0, 0, self.width, self.height, fill=color(self.r, self.g, self.b, self.opacity))
        
class ToolBar(InteractiveLayer):
    
    def __init__(self, **kwargs):
        super(ToolBar, self).__init__(**kwargs)
        self.opacity = 0.1
        self.y = -60
        self.duration = 0.1
        
    def draw(self):
        colorplane(0, 0, self.width, self.height, color(0.8, 0.8, 0.85, self._opacity.now), color(0.7, 0.7, 0.7, self._opacity.now))
        rect(0, self.height-1, self.width, 1, fill=color(0.7, 0.7, 0.7, self._opacity.now))
        
    def on_mouse_enter(self, x, y):
        self.y = 0
        self.opacity = 1.0
        
    def on_mouse_leave(self, x, y):
        self.y = -60
        self.opacity = 0.1

class ScaleUp(Button):
    
    def on_action(self):
        global editableObject
        editableObject.scaling *= 2.0
        scaler.rotation += 5
        
    def draw(self):
        super(ScaleUp, self).draw()
        rect(0, 0, 30, 30, fill=color(1,1,1))
        
class ScaleDown(Button):
    
    def on_action(self):
        global editableObject
        editableObject.scaling *= 0.5
        scaler.rotation -= 5

    def draw(self):
        super(ScaleDown, self).draw()
        rect(0, 0, 10, 10, fill=color(1,1,1))
        
class RotateCCW(Button):
    
    def on_action(self):
        global editableObject
        editableObject.rotation += 5
        
    def draw(self):
        super(RotateCCW, self).draw()
        rotate(5)
        rect(20, 20, 40, 40, fill=color(1,1,1))
        
class RotateCW(Button):
    
    def on_action(self):
        global editableObject
        editableObject.rotation -= 5

    def draw(self):
        super(RotateCW, self).draw()
        rotate(-5)
        rect(20, 20, 40, 40, fill=color(1,1,1))
        
class Scaler(Slider):

    def __init__(self, **kwargs):
        super(Scaler, self).__init__(min_value=0.0, max_value=10.0, value=1.0, **kwargs)
    
    def on_action(self):
        global editableObject
        editableObject.scaling = self.value
        
class Rotator(Slider):
    def __init__(self, **kwargs):
        super(Rotator, self).__init__(min_value=-90.0, max_value=90.0, value=0.0, **kwargs)
    
    def on_action(self):
        global editableObject
        editableObject.rotation = -self.value
        
editableObject = EditableObject(x=WIDTH/2, y=HEIGHT/2, width=50, height=50)

toolBar = ToolBar(x=0, y=0, width=WIDTH, height=80)
toolBar.append(ScaleDown(x=10, y=10, width=60, height=60))
toolBar.append(ScaleUp(x=80, y=10, width=60, height=60))
toolBar.append(RotateCCW(x=150, y=10, width=60, height=60))
toolBar.append(RotateCW(x=220, y=10, width=60, height=60))
toolBar.append(Button(x=290, y=10, width=60, height=60))

background(0.2, 0.2, 0.22)
canvas.append(toolBar)
canvas.append(editableObject)
scaler = Scaler(x=300, y=200, width=80, height=16)
rotator = Rotator(x=300, y=230, width=80, height=16)
canvas.append(scaler)
canvas.append(rotator)

canvas.append(Label(text="hello", x=20, y=120,width=100,height=100))
#canvas.append(label)

canvas.run()
