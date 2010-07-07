# Native GUI controle.
# Authors: Frederik De Bleser, Tom De Smedt
# License: GPL (see LICENSE.txt for details).
# Copyright (c) 2008 City In A Bottle (cityinabottle.org)

import os
from glob import glob
from time import time

from pyglet.text.layout import IncrementalTextLayout
from pyglet.text.caret  import Caret

from nodebox.graphics.geometry import distance, clamp, Bounds
from nodebox.graphics import \
    Layer, Color, Image, image, crop, \
    Text, font, NORMAL, BOLD, CENTER, \
    cursor, DEFAULT, HAND, TEXT, \
    LEFT, RIGHT, UP, DOWN, TAB, ENTER, BACKSPACE

def popdefault(dict, key, default=None):
    """ Pops the given key from the dictionary and returns its value (or default).
    """
    if key in dict: 
        return dict.pop(key)
    return default
    
def find(match=lambda item: False, list=[]):
    """ Returns the first item in the list for which match(item)=True, or None.
    """
    for item in list:
        if match(item): return item

#=====================================================================================================

#--- Theme -------------------------------------------------------------------------------------------

class Theme(dict):
    
    def __init__(self, path):
        """ A theme defines the source images for controls and font settings for labels.
            A theme is loaded from a given folder path (containing PNG images and TTF font files).
            The default theme is in nodebox/graphics/gui/theme/
            Copy this folder and modify it to create a custom theme.
        """
        images = glob(os.path.join(path, "*.png"))
        images = [(os.path.basename(os.path.splitext(f)[0]), f) for f in images]
        fonts  = glob(os.path.join(path, "*.ttf"))
        fonts  = [(os.path.basename(os.path.splitext(f)[0]), font(file=f)) for f in fonts]
        fonts  = [f[0] for f in fonts]
        dict.__init__(self, images)
        self["fonts"]      = fonts
        self["font"]       = fonts and fonts[-1] or "Arial" # Filename is assumed to be fontname.
        self["fontsize"]   = 10
        self["fontweight"] = NORMAL
        self["text"]       = Color(1.0)

theme = Theme(os.path.join(os.path.dirname(__file__), "theme")) 

#=====================================================================================================

#--- Control -----------------------------------------------------------------------------------------

class Control(Layer):
    
    def __init__(self, id=None, **kwargs):
        """ Base class for GUI controls.
            The Control class inherits from Layer so it must be appended to the canvas (or a container)
            to receive events and get drawn.
            An id can be given to uniquely identify the control.
            If the control is part of a Panel, it can be retrieved with Panel.control_id.
        """
        Layer.__init__(self, **kwargs)
        self.id        = id
        self.src       = {}    # Collection of source images.
        self.pressed   = False # True when mouse is pressed in the control.
        self.dragged   = False # True when mouse is dragged in the control.
        self.enabled   = True  # Enable event listener.
        self.duration  = 0     # Disable tweening.
        self._controls = {}    # Lazy dictionary of child controls indexed by id.
        self._press    = None

    # Control width and height can't be modified after creation.
    # Internally, use Layer._set_width() and Layer._set_height().
    @property
    def width(self):
        return self._get_width()
    @property
    def height(self):
        return self._get_height()

    def on_mouse_enter(self, mouse): 
        mouse.cursor = HAND
    def on_mouse_leave(self, mouse): 
        mouse.cursor = DEFAULT
        
    def on_mouse_press(self, mouse):
        if  self._press and \
        abs(self._press[0] - mouse.x) < 2 and \
        abs(self._press[1] - mouse.y) < 2 and \
            self._press[2] == mouse.button and \
            self._press[3] == mouse.modifiers and \
            self._press[4] - time() > -0.4:
            self._press = None
            self.on_mouse_doubleclick(mouse)
        self._press = (mouse.x, mouse.y, mouse.button, mouse.modifiers, time())
        self.pressed = True
    def on_mouse_drag(self, mouse):
        self.dragged = True
    def on_mouse_release(self, mouse):
        self.pressed = False
        self.dragged = False
    def on_mouse_doubleclick(self, mouse):
        pass
        
    def on_key_press(self, key):
        for control in self: control.on_key_press(key)
    def on_key_release(self, key):
        for control in self: control.on_key_release(key)
    
    def on_action(self):
        """ Override this method with a custom action.
        """
        pass
        
    def reset(self):
        self.pressed = False
        self.dragged = False

    def _draw(self):
        Layer._draw(self)
    
    # Control._pack() is called internally to layout child controls.
    # This should not happen in Control.update(), which is called every frame.
    def _pack(self):
        pass

    # With transformed=True, expensive matrix transformations are done.
    # Turn off, controls are not meant to be rotated or scaled.        
    def layer_at(self, x, y, clipped=False, transformed=True, enabled=False, _covered=False):
        return Layer.layer_at(self, x, y, clipped, False, enabled, _covered)

    def __getattr__(self, k):
        # Retrieves the given attribute.
        # Retrieves the child control with the given id.
        if k in self.__dict__:
            return self.__dict__[k]
        if k in self._controls:
            return self._controls[k]
        # Nested controls' id might have changed (however unlikely).
        # Recreate the cache and search again.
        for ctrl in self:
            if isinstance(ctrl, Control) and ctrl.id:
                self._controls[ctrl.id] = ctrl
            if isinstance(ctrl, Layout):
                [self._controls.setdefault(ctrl.id, ctrl) for ctrl in ctrl if ctrl.id]
        if k in self._controls:
            return self._controls[k]
        raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__.__name__, k)

#=====================================================================================================

#--- Label -------------------------------------------------------------------------------------------

class Label(Control):
    
    def __init__(self, caption, **kwargs):
        """ A label displaying the given caption, centered in the label's (width, height)-box.
            The label does not receive any events.
            Optional parameters can include fill, font, fontsize, fontweight.
        """
        txt = Text(caption, **{
               "fill" : popdefault(kwargs, "fill", theme["text"]),
               "font" : popdefault(kwargs, "font", theme["font"]),
           "fontsize" : popdefault(kwargs, "fontsize", theme["fontsize"]),
         "fontweight" : popdefault(kwargs, "fontweight", theme["fontweight"]),
         "lineheight" : 1,
              "align" : CENTER
        })
        kwargs.setdefault("width", txt.metrics[0])
        kwargs.setdefault("height", txt.metrics[1])
        Control.__init__(self, **kwargs)
        self.enabled = False # Pass on events to the layers underneath.
        self._text   = txt
        self._pack()      

    def _get_caption(self):
        return self._text.text
    def _set_caption(self, string):
        self._text.text = string
        self._pack()
        
    caption = property(_get_caption, _set_caption)

    @property
    def fonts(self):
        return self._text.font
    @property
    def fontsize(self):
        return self._text.fontsize
    @property
    def fontweight(self):
        return self._text.fontweight

    def _pack(self):
        # Center the text inside the label.
        self._text.x = 0.5 * (self.width - self._text.metrics[0])
        self._text.y = 0.5 * (self.height - self._text.metrics[1])  

    def draw(self):
        self._text.draw()

#=====================================================================================================

#--- BUTTON ------------------------------------------------------------------------------------------

class Button(Control):
    
    def __init__(self, caption="", action=None, width=125, **kwargs):
        """ A clickable button that will fire Button.on_action() when clicked.
            The action handler can be defined in a subclass, or given as a function.
        """
        Control.__init__(self, width=width, **kwargs)
        img, w = Image(theme["button"]), 20
        self.src = {
            "face" : crop(img, w, 0, 1, img.height),
            "cap1" : crop(img, 0, 0, w, img.height),
            "cap2" : crop(img, img.width-w, 0, w, img.height),
        }
        if action:
            # Override the Button.on_action() method from the given function.
            self.set_method(action, name="on_action")
        popdefault(kwargs, "width")
        popdefault(kwargs, "height")
        self.append(Label(caption, **kwargs))
        self._pack()
    
    def _get_caption(self): 
        return self[0].caption
    def _set_caption(self, string):
        self[0].caption = string
        self._pack()
        
    caption = property(_get_caption, _set_caption)
    
    def _pack(self):
        # Button size can not be smaller than its caption.
        w = max(self.width, self[0].width + self[0].fontsize * 2)
        self._set_width(w)
        self._set_height(self.src["face"].height)
    
    def update(self):
        # Center the text inside the button.
        # This happens each frame because the position changes when the button is pressed.
        self[0].x = 0.5 * (self.width - self[0].width)
        self[0].y = 0.5 * (self.height - self[0].height) - self.pressed

    def draw(self):
        clr = self.pressed and (0.75, 0.75, 0.75) or (1.0, 1.0, 1.0)
        im1, im2, im3 = self.src["cap1"], self.src["cap2"], self.src["face"]
        image(im1, 0, 0, height=self.height, color=clr)
        image(im2, x=self.width-im2.width, height=self.height, color=clr)
        image(im3, x=im1.width, width=self.width-im1.width-im2.width, height=self.height, color=clr)

    def on_mouse_release(self, mouse):
        Control.on_mouse_release(self, mouse)
        if self.contains(mouse.x, mouse.y, transformed=False):
            # Only fire event if mouse is actually released on the button.
            self.on_action()

#--- ACTION ------------------------------------------------------------------------------------------

class Action(Control):
    
    def __init__(self, action=None, **kwargs):
        """ A clickable button that will fire Action.on_action() when clicked.
            Actions display an icon instead of a text caption.
            Actions are meant to be used for interface management:
            e.g. closing or minimizing a panel, navigating to the next page, ...
        """
        Control.__init__(self, **kwargs)
        self.src = {"face": Image(theme["action"])}
        self._pack()
        if action:
            # Override the Button.on_action() method from the given function.
            self.set_method(action, name="on_action")
    
    def _pack(self):
        self._set_width(self.src["face"].width)
        self._set_height(self.src["face"].height)
    
    def draw(self):
        clr = self.pressed and (0.75, 0.75, 0.75) or (1.0, 1.0, 1.0)
        image(self.src["face"], 0, 0, color=clr)
            
    def on_mouse_release(self, mouse):
        Control.on_mouse_release(self, mouse)
        if self.contains(mouse.x, mouse.y, transformed=False):
            # Only fire event if mouse is actually released on the button.
            self.on_action()
        
class Close(Action):
    
    def __init__(self, action=None, **kwargs):
        """ An action that hides the parent control (e.g. a Panel) when pressed.
        """
        Action.__init__(self, action, **kwargs)
        self.src["face"] = Image(theme["action-close"])
        
    def on_action(self):
        self.parent.hidden = True

#=====================================================================================================

#--- SLIDER ------------------------------------------------------------------------------------------

class Handle(Control):
    
    def __init__(self, parent):
        # The slider handle can protrude from the slider bar,
        # so it is a separate layer that fires its own events.
        Control.__init__(self,
            width = parent.src["handle"].width,
           height = parent.src["handle"].height)
        self.parent = parent
        
    def on_mouse_press(self, mouse):
        self.parent.on_mouse_press(mouse)
    def on_mouse_drag(self, mouse):
        self.parent.on_mouse_drag(mouse)
    def on_mouse_release(self, mouse):
        self.parent.on_mouse_release(mouse)
        
    def draw(self):
        clr = self.parent.pressed and (0.75, 0.75, 0.75) or (1.0, 1.0, 1.0)
        image(self.parent.src["handle"], 0, 0, color=clr)

class Slider(Control):
    
    def __init__(self, default=0.5, min=0.0, max=1.0, steps=100, width=125, **kwargs):
        """ A draggable slider that will fire Slider.on_action() when dragged.
            The slider's value can be retrieved with Slider.value.
        """
        Control.__init__(self, width=width, **kwargs)
        self.min     = min     # Slider minimum value.
        self.max     = max     # Slider maximum value.
        self.default = default # Slider default value.
        self.value   = default # Slider current value.
        self.steps   = steps   # Number of steps from min to max.
        img, w = Image(theme["slider"]), 5
        self.src = {
            "face1" : crop(img, w, 0, 1, img.height),
            "face2" : crop(img, img.width-w, 0, 1, img.height),
             "cap1" : crop(img, 0, 0, w, img.height),
             "cap2" : crop(img, img.width-w, 0, w, img.height),
           "handle" : Image(theme["slider-handle"])
        }
        # The handle is a separate layer.
        self.append(Handle(self))
        self._pack()

    def _get_value(self):
        return self.min + self._t * (self.max-self.min)
    def _set_value(self, value):
        self._t = clamp(float(value-self.min) / (self.max-self.min or -1), 0.0, 1.0)
        
    value = property(_get_value, _set_value)
        
    @property
    def relative(self):
        """ Yields the slider position as a relative number (0.0-1.0).
        """
        return self._t

    def _pack(self):
        w = max(self.width, self.src["cap1"].width + self.src["cap2"].width)
        self._set_width(w)
        self._set_height(self.src["face1"].height)

    def reset(self):
        Control.reset(self)
        self.value = self.default
    
    def update(self):
        # Update the handle's position, before Slider.draw() occurs (=smoother).
        self[0].x = self._t * self.width - 0.5 * self[0].width
        self[0].y = 0.5 * (self.height - self[0].height)
    
    def draw(self):
        t = self._t * self.width
        im1, im2, im3, im4  = self.src["cap1"], self.src["cap2"], self.src["face1"], self.src["face2"]
        image(im1, x=0, y=0)
        image(im2, x=self.width-im2.width, y=0)
        image(im3, x=im1.width, y=0, width=t-im1.width)
        image(im4, x=t, y=0, width=self.width-t-im2.width+1)

    def on_mouse_press(self, mouse):
        self.pressed = True
        x0, y0 = self.absolute_position() # Can be nested in other layers.
        step = 1.0 / max(self.steps, 1)
        # Calculate relative value from the slider handle position.
        # The inner width is a bit smaller to accomodate for the slider handle.
        # Clamp the relative value to the nearest step.
        self._t = (mouse.x-x0-self.height*0.5) / float(self.width-self.height)
        self._t = self._t - self._t % step + step 
        self._t = clamp(self._t, 0.0, 1.0)
        self.on_action()
    
    def on_mouse_drag(self, mouse):
        self.dragged = True
        self.on_mouse_press(mouse)

#=====================================================================================================

#--- FLAG --------------------------------------------------------------------------------------------

class Flag(Control):
    
    def __init__(self, default=False, **kwargs):
        """ A checkbox control that fires Flag.on_action() when checked.
            The checkbox value can be retrieved with Flag.value.
        """
        Control.__init__(self, **kwargs)
        self.default = bool(default) # Flag default value.
        self.value   = bool(default) # Flag current value.
        self.src = {
            "face" : Image(theme["flag"]),
         "checked" : Image(theme["flag-checked"]),
        }
        self._pack()
        
    def _pack(self):
        self._set_width(self.src["face"].width)
        self._set_height(self.src["face"].height)
    
    def reset(self):
        self.value = self.default
    
    def draw(self):
        image(self.value and self.src["checked"] or self.src["face"])
        
    def on_mouse_release(self, mouse):
        Control.on_mouse_release(self, mouse)
        if self.contains(mouse.x, mouse.y, transformed=False):
            # Only change status if mouse is actually released on the button.
            self.value = not self.value
            self.on_action()

Checkbox = CheckBox = Flag

#=====================================================================================================

#--- PANEL -------------------------------------------------------------------------------------------    

class Panel(Control):
    
    def __init__(self, caption="", fixed=False, modal=True, width=175, height=250, **kwargs):
        """ A panel containing other controls that can be dragged when Panel.fixed=False.
            Controls or (Layout groups) can be added with Panel.append().
        """
        Control.__init__(self, width=max(width,60), height=max(height,60), **kwargs)
        img, w = Image(theme["panel"]), 30
        self.src = {
           "cap1" : crop(img, 0, img.height-w, w, w),
           "cap2" : crop(img, img.width-w, img.height-w, w, w),
           "cap3" : crop(img, 0, 0, w, w),
           "cap4" : crop(img, img.width-w, 0, w, w),
            "top" : crop(img, w+1, img.height-w, 1, w),
         "bottom" : crop(img, w+1, 0, 1, w),
           "left" : crop(img, 0, w+1, w, 1),
          "right" : crop(img, img.width-w, w+1, w, 1),
           "face" : crop(img, w+1, w+1, 1, 1)
        }
        popdefault(kwargs, "width")
        popdefault(kwargs, "height")
        self.append(Label(caption, **kwargs))
        self.append(Close())
        self.fixed = fixed # Draggable?
        self.modal = modal # Closeable?
        self._pack()

    @property
    def _get_caption(self):
        return self._caption.text
    def _set_caption(self, str):
        self._caption.text = str
        self._pack()

    @property
    def controls(self):
        return iter(self[2:]) # self[0] is the Label,
                              # self[1] is the Close action.
    
    def insert(self, i, control):
        """ Inserts the control, or inserts all controls in the given Layout.
        """
        if isinstance(control, Layout):
            # If the control is actually a Layout (e.g. ordered group of controls), apply it.
            control.apply()
        Layer.insert(self, i, control)
        
    def append(self, control):
        self.insert(len(self), control)
    def extend(self, controls):
        for control in controls: self.append(control)

    def _pack(self):
        # Center the caption in the label's header.
        # Position the close button in the top right corner.
        self[0].x = 0.5 * (self.width - self[0].width)
        self[0].y = self.height - self.src["top"].height + 0.5 * (self.src["top"].height - self[0].height)
        self[1].x = self.width - self[1].width - 4
        self[1].y = self.height - self[1].height - 2
        
    def pack(self, padding=10):
        """ Resizes the panel to the most compact size,
            based on the position and size of the controls in the panel.
        """
        def _visit(control):
            if control not in (self, self[0], self[1]):
                self._b = self._b and self._b.union(control.bounds) or control.bounds
        self._b = None
        self.traverse(_visit)
        for control in self.controls:
            control.x += padding - self._b.x
            control.y += padding - self._b.y
        self._set_width( padding + self._b.width  - self._b.x + padding)
        self._set_height(padding + self._b.height - self._b.y + padding + self.src["top"].height)
        self._pack()
    
    def update(self):
        self[1].hidden = self.modal
    
    def draw(self):
        im1, im2, im3 = self.src["cap1"], self.src["cap2"],  self.src["top"]
        im4, im5, im6 = self.src["cap3"], self.src["cap4"],  self.src["bottom"]
        im7, im8, im9 = self.src["left"], self.src["right"], self.src["face"]
        image(im1, 0, self.height-im1.height)
        image(im2, self.width-im2.width, self.height-im2.height)
        image(im3, im1.width, self.height-im3.height, width=self.width-im1.width-im2.width)
        image(im4, 0, 0)
        image(im5, self.width-im5.width, 0)
        image(im6, im4.width, 0, width=self.width-im4.width-im5.width)
        image(im7, 0, im4.height, height=self.height-im1.height-im4.height)
        image(im8, self.width-im8.width, im4.height, height=self.height-im2.height-im5.height)
        image(im9, im4.width, im6.height, width=self.width-im7.width-im8.width, height=self.height-im3.height-im6.height)
            
    def on_mouse_enter(self, mouse): 
        mouse.cursor = DEFAULT

    def on_mouse_press(self, mouse):
        self.pressed = True
        self.dragged = not self.fixed and mouse.y > self.y+self.height-self.src["top"].height

    def on_mouse_drag(self, mouse):
        if self.dragged:
            self.x += mouse.vx
            self.y += mouse.vy
    
    def open(self):
        self.hidden = False
    def close(self):
        self.hidden = True

#=====================================================================================================

#--- Editable ----------------------------------------------------------------------------------------

class Editable(Control):
    
    def __init__(self, value="", width=125, height=30, padding=(0,0), wrap=True, **kwargs):
        """ An editable text box.
            When clicked, it has the focus and can receive keyboard events.
            With wrap=True, several lines of text will wrap around the width.
            Optional parameters can include fill, font, fontsize, fontweight.
        """
        txt = Text(value or " ", **{
               "fill" : popdefault(kwargs, "fill", Color(0,0.9)),
               "font" : popdefault(kwargs, "font", theme["font"]),
           "fontsize" : popdefault(kwargs, "fontsize", theme["fontsize"]),
         "fontweight" : popdefault(kwargs, "fontweight", theme["fontweight"]),
         "lineheight" : 1,
              "align" : LEFT
        })
        kwargs["width"]  = width
        kwargs["height"] = height
        Control.__init__(self, **kwargs)
        self.focus    = False
        self._padding = padding
        self._empty   = value == "" and True or False
        self._editor  = IncrementalTextLayout(txt._label.document, width, height, multiline=wrap)
        self._editor.content_valign = wrap and "top" or "center"
        self._editor.caret = Caret(self._editor)
        self._editor.caret.visible = False
        Editable._pack(self) # On init, call Editable._pack(), not the derived Field._pack().
        
    def _pack(self):
        self._editor.x = self._padding[0]
        self._editor.y = self._padding[1]
        self._editor.width  = max(0, self.width  - self._padding[0] * 2)
        self._editor.height = max(0, self.height - self._padding[1] * 2)

    def _get_value(self):
        # IncrementalTextLayout in Pyglet 1.1.4 has a bug with the empty string.
        # We keep track of empty strings with Editable._empty to avoid the bug.
        return not self._empty and self._editor.document.text or u""
    def _set_value(self, string):
        self._editor.begin_update()
        self._editor.document.text = string or " "
        self._editor.end_update()
        self._empty = string == "" and True or False
        
    value = property(_get_value, _set_value)

    def _get_selection(self):
        # Yields a (start, stop)-tuple with the indices of the current selected text.
        i = self._editor.selection_start
        j = self._editor.selection_end
        return min(i,j), max(i,j)
    def _set_selection(self, (i,j)):
        self._editor.selection_start = max(min(i, j), 0)
        self._editor.selection_end   = min(max(i, j), len(self.value))
        
    selection = property(_get_selection, _set_selection)
    
    @property
    def selected(self):
        # Yields True when text is currently selected.
        return self.selection[0] != self.selection[1]
        
    @property
    def cursor(self):
        # Yields the index at the text cursor (caret).
        return self._editor.caret.position
    
    def index(self, x, y):
        """ Returns the index of the character in the text at position x, y.
        """
        x0, y0 = self.absolute_position()
        i = self._editor.get_position_from_point(x-x0, y-y0)
        if self._editor.get_point_from_position(0)[0] > x-x0: # Pyglet bug?
            i = 0
        if self._empty:
            i = 0
        return i
    
    def on_mouse_enter(self, mouse):
        mouse.cursor = TEXT
        
    def on_mouse_press(self, mouse):
        i = self.index(mouse.x, mouse.y)
        self.selection = (i, i)
        self._editor.caret.visible = True
        self._editor.caret.position = i
        self.focus = True
        Control.on_mouse_press(self, mouse)
        
    def on_mouse_release(self, mouse):
        if not self.dragged:
            self._editor.caret.position = self.index(mouse.x, mouse.y)
        Control.on_mouse_release(self, mouse)
        
    def on_mouse_drag(self, mouse):
        i = self.index(mouse.x, mouse.y)
        s = self.selection
        self.selection = i > s[0] and (s[0], i) or (i, s[1])
        self._editor.caret.visible = False
        Control.on_mouse_drag(self, mouse)

    def on_mouse_doubleclick(self, mouse):
        # Select the word at the mouse position. 
        # Words are delimited by non-alphanumeric characters.
        i = self.index(mouse.x, mouse.y)
        delimiter = lambda ch: not (ch.isalpha() or ch.isdigit())
        if i  < len(self.value) and delimiter(self.value[i]):
            self.selection = (i, i+1); return
        if i == len(self.value) and self.value != "" and delimiter(self.value[i-1]):
            self.selection = (i-1, i); return
        a = find(lambda (i,ch): delimiter(ch), enumerate(reversed(self.value[:i])))
        b = find(lambda (i,ch): delimiter(ch), enumerate(self.value[i:]))
        a = a and i-a[0] or 0
        b = b and i+b[0] or len(self.value)
        self.selection = (a, b)

    def on_key_press(self, key):
        if self.focus:
            self._editor.caret.visible = True
            i = self._editor.caret.position
            if   key.code == LEFT:
                # The left arrow moves the text cursor to the left.
                self._editor.caret.position = max(i-1, 0)
            elif key.code == RIGHT:
                # The right arrow moves the text cursor to the right.
                self._editor.caret.position = min(i+1, len(self.value))
            elif key.code in (UP, DOWN):
                # The up arrows moves the text cursor to the previous line.
                # The down arrows moves the text cursor to the next line.
                y = key.code == UP and -1 or +1
                n = self._editor.get_line_count()
                i = self._editor.get_position_on_line(
                    max(self._editor.get_line_from_position(i)+y, 0),
                        self._editor.get_point_from_position(i)[0])
                self._editor.caret.position = i
            elif key.code == TAB:
                # The tab key navigates away from the control.
                self._editor.caret.position = 0
                self._editor.caret.visible = self.focus = False
            elif key.code == ENTER:
                # The enter key executes on_action() and navigates away from the control.
                self._editor.caret.position = 0
                self._editor.caret.visible = self.focus = False
                self.on_action()
            elif key.code == BACKSPACE and self.selected:
                # The backspace key removes the character at the text cursor.
                self.value = self.value[:self.selection[0]] + self.value[self.selection[1]:]
                self._editor.caret.position = max(self.selection[0], 0)
            elif key.code == BACKSPACE and i > 0:
                # The backspace key removes the current text selection.
                self.value = self.value[:i-1] + self.value[i:]
                self._editor.caret.position = max(i-1, 0)
            elif key.char:
                # Character input is inserted at the text cursor.
                self.value = self.value[:i] + key.char + self.value[i:]
                self._editor.caret.position = min(i+1, len(self.value))
            self.selection = (0,0)
    
    def draw(self):
        self._editor.draw()

#--- Field -------------------------------------------------------------------------------------------

class Field(Editable):
    
    def __init__(self, value="", hint="", action=None, width=125, padding=5, **kwargs):
        """ A single-line text input field.
            The string value can be retrieved with Field.value.
        """
        Editable.__init__(self, value, width, padding=(padding,0), wrap=False, **kwargs)
        img, w = Image(theme["field"]), 10
        self.src = {
            "face" : crop(img, w, 0, 1, img.height),
            "cap1" : crop(img, 0, 0, w, img.height),
            "cap2" : crop(img, img.width-w, 0, w, img.height),
        }
        if action:
            # Override the Button.on_action() method from the given function.
            self.set_method(action, name="on_action")
        self.default = value
        self.append(Label(hint, fill=Color(0, 0.4)))
        self._pack()

    def _get_hint(self):
        return self[0].caption
    def _set_hint(self, string):
        self[0].caption = string

    def reset(self):
        self.value = self.default

    def _pack(self):
        Editable._pack(self)
        w = max(self.width, self.src["cap1"].width + self.src["cap2"].width)
        self._set_width(w)
        self._set_height(self.src["face"].height)
        # Position the hint text (if no other text is in the field):
        self[0].x = self._padding[0]
        self[0]._set_height(self.height)
        self[0]._pack()
    
    def on_action(self):
        pass
        
    def update(self):
        self[0].hidden = self.focus or self.value != ""
    
    def draw(self):
        im1, im2, im3 = self.src["cap1"], self.src["cap2"], self.src["face"]
        image(im1, 0, 0, height=self.height)
        image(im2, x=self.width-im2.width, height=self.height)
        image(im3, x=im1.width, width=self.width-im1.width-im2.width, height=self.height)
        Editable.draw(self)

#=====================================================================================================

#--- Layout ------------------------------------------------------------------------------------------

class Layout(Layer):
    
    def __init__(self, **kwargs):
        """ A group of controls with a specific layout.
            Controls can be added with Layout.append().
            The layout will be applied when Layout.apply() is called.
            This happens automatically if a layout is appended to a Panel.
        """
        kwargs["x"] = kwargs["y"] = kwargs["width"] = kwargs["height"] = 0
        Layer.__init__(self, **kwargs)

    def on_key_press(self, key):
        for control in self: control.on_key_press(key)
    def on_key_release(self, key):
        for control in self: control.on_key_release(key)
    
    def apply(self, padding=0):
        """ Adjusts the position and size of the controls to match the layout.
        """
        pass

#--- Layout: Rows ------------------------------------------------------------------------------------

class Rows(Layout):

    def __init__(self, controls=[], width=125):
        """ A layout where each control appears on a new line.
            Each control has an associated text caption, displayed to the left of the control.
            The given width defines the desired width for each control.
        """
        Layout.__init__(self)
        self.maxwidth = width
        self.controls = []
        self.captions = []
        self.extend(controls)

    def insert(self, i, control, caption=""):
        """ Inserts a new control to the layout, with an associated caption.
            Each control will be drawn in a new row.
        """
        self.controls.insert(i, control)
        self.captions.insert(i, Label(caption.upper(), 
            fontsize = theme["fontsize"] * 0.8, 
                fill = theme["text"].rgb+(theme["text"].a * 0.8,)))
        Layout.insert(self, i, self.controls[i])
        Layout.insert(self, i, self.captions[i])
        
    def append(self, control, caption=""):
        self.insert(len(self)/2, control, caption)
    def extend(self, controls):
        for control in controls:
            caption, control = isinstance(control, tuple) and control or ("", control)
            self.append(control, caption)
    def remove(self, control):
        self.pop(self.controls.index(control))
    def pop(self, i):
        self.captions.pop(i); return self.controls.pop(i)

    def apply(self, padding=20):
        """ Adjusts the position and width of all the controls in the layout:
            - each control is placed next to its caption, with padding in between and around,
            - each caption is aligned to the right, and centered vertically,
            - the width of all Label, Button, Sliderm, Field controls is evened out.
        """
        width = max([caption.width for caption in self.captions])
        dx = 0
        dy = padding
        for caption, control in reversed(zip(self.captions, self.controls)):
            caption.x = dx + padding * 1.0 + width - caption.width
            control.x = dx + padding * 1.5 + width
            caption.y = dy + 0.5 * (control.height - caption.height)
            control.y = dy
            if isinstance(control, (Label, Button, Slider, Field)):
                control._set_width(self.maxwidth)
                control._pack()
            dy += max(caption.height, control.height, 10) + 0.5 * padding
        self.width  = width + self.maxwidth + padding * 2.5
        self.height = dy + padding * 0.5

