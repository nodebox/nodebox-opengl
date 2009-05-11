from nodebox.graphics import context
from time import time
import pyglet
from pyglet.gl import *

from nodebox.graphics import Layer, Canvas, Color, \
    canvas, gradient, run, size, rect, color, background, random, rotate, text, push, translate, pop, \
    LEFT, RIGHT
size(700, 700)
WIDTH, HEIGHT = 700, 700

class CheckBox(Layer):

    def __init__(self, label="", checked=True, **kwargs):
        self.label = label
        self.checked = checked
        kwargs['width'] = kwargs.get('width', 150)
        kwargs['height'] = kwargs.get('height', 16)
        super(CheckBox, self).__init__(**kwargs)

    def draw(self):
        sz = self.height
        rect(0, 0, sz, sz, stroke=color(0))
        if self.checked:
            rect(2, 2, sz-4, sz-4, fill=color(0))
        text(self.label, sz + 5, 4, fontsize=8)
        
class Label(Layer):
    
    def __init__(self, label="", fontsize=8, align=None, fill=color(0), **kwargs):
        self.label = label
        self.fontsize = fontsize
        self.fill = fill
        self.align = align
        kwargs['width'] = kwargs.get('width', 150)
        kwargs['height'] = kwargs.get('height', 16)
        super(Label, self).__init__(**kwargs)
        
    def draw(self):
        # The '4' offsets the label a bit
        text(self.label, 0, 4, width=self.width, fontsize=self.fontsize, align=self.align, fill=self.fill)
        
class TextField(Layer):
    
    def __init__(self, text="", **kwargs):
        self.text = text
        kwargs['width'] = kwargs.get('width', 150)
        kwargs['height'] = kwargs.get('height', 16)
        super(TextField, self).__init__(**kwargs)
        
    def draw(self):
        rect(0, 0, self.width, self.height, stroke=color(0))
        
class VerticalBox(Layer):

    def __init__(self, margin=3, **kwargs):
        self.margin = margin
        kwargs['width'] = kwargs.get('width', 150)
        # Height should grow to fill container
        kwargs['height'] = kwargs.get('height', 16)
        super(VerticalBox, self).__init__(**kwargs)
        
    def layout(self):
        #child_count = len(self.children)
        y = 0
        for child in self:
            child.y = y
            y += child.height + self.margin
            print child.x, child.y, child.width, child.height

class FormBox(Layer):
    
    def __init__(self, margin=5, label_width=150, **kwargs):
        self.margin = margin
        self.label_width = label_width
        super(FormBox, self).__init__(**kwargs)
        
    def append(self, layer, label=""):
        super(FormBox, self).append(Label(label, align=RIGHT))
        super(FormBox, self).append(layer)
        
    def layout(self):
        # Form layouts have two implicit columns:
        # the first element is the label, the second is the layer.
        state_label = True
        y = 0
        for child in self:
            if state_label:
                child.x = 0
                child.y = y
                child.width = self.label_width
            else:
                child.x = self.label_width + self.margin
                child.y = y
                y += child.height + self.margin
            state_label = not state_label
            
    def on_mouse_press(self, x, y, button, modifiers):
        from random import uniform
        for child in self:
            child.duration = 0.2
            child.rotation = uniform(-40.0, 40.0)
            child.scale = uniform(0.1, 3.0)

layout = FormBox(x=5, y=600, width=WIDTH, height=HEIGHT)
layout.append(CheckBox("Enable"))
layout.append(CheckBox("Show Label"))
layout.append(TextField("Label"), "Label")
layout.layout()

canvas.append(layout)
canvas.run()