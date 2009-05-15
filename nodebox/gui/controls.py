from nodebox.graphics import InteractiveLayer, Color
from nodebox.graphics import rect, color, text, LEFT

class Label(InteractiveLayer):

    def __init__(self, text="", font='Verdana', fontsize=8, lineheight=1.0, align=LEFT, fill=color(0), **kwargs):
        super(Label, self).__init__(**kwargs)
        self.text = text
        self.font = font
        self.fontsize = fontsize
        self.lineheight = lineheight
        self.align = align
        self.fill = fill
        
    def draw(self):
        text(self.text, 0, 0, width=self.width, 
            font=self.font, fontsize=self.fontsize, lineheight=self.lineheight, align=self.align,
            fill=self.fill)

class Button(InteractiveLayer):
    
    def __init__(self, text="", **kwargs):
        super(Button, self).__init__(**kwargs)
        self.hover_state = False
        self.opacity = 0.4
        
    def draw(self):
        rect(0, 0, self.width, self.height, fill=color(0.2, 0.2, 0.2, self.opacity))
        
    def on_mouse_enter(self, x, y):
        self.opacity = 0.7
        self.hover_state = True

    def on_mouse_leave(self, x, y):
        self.opacity = 0.4
        self.hover_state = False
        
    def on_mouse_press(self, x, y, button, modifiers):
        self.opacity = 1.0
        
    def on_mouse_release(self, x, y, button, modifiers):
        self.opacity = 0.7
        self.on_action()

    def on_action(self):
        pass
        
class Slider(InteractiveLayer):
    
    def __init__(self, value=0.0, min_value=0.0, max_value=100.0, **kwargs):
        super(Slider, self).__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value
        self.value = value
        
    def draw(self):
        range = self.max_value - self.min_value
        pos = (self.value - self.min_value) / range
        pos *= self.width
        rect(0, 0+5, self.width, self.height-10, fill=color(0.5, 0.5, 0.5, self.opacity))
        rect(pos-4, 0, 8, self.height, fill=color(0.2, 0.2, 0.2, self.opacity))
        
    def on_mouse_press(self, x, y, button, modifiers):
        x -= self.x
        y -= self.y
        v = float(x) / self.width
        v = min(1.0, max(0.0, v))
        v = self.min_value + (self.max_value - self.min_value) * v
        self.value = v
        self.on_action()
        
    def on_mouse_drag(self, x, y, dx, dy, button, modifiers):
        self.on_mouse_press(x, y, button, modifiers)
        self.on_action()
        
    def on_action(self):
        pass

