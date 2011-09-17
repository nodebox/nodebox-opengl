#=== CONTROLS ========================================================================================
# Native GUI controls.
# Authors: Tom De Smedt, Frederik De Bleser
# License: BSD (see LICENSE.txt for details).
# Copyright (c) 2008 City In A Bottle (cityinabottle.org)
# http://cityinabottle.org/nodebox

import os
from glob import glob
from time import time

from pyglet.text.layout import IncrementalTextLayout
from pyglet.text.caret  import Caret

from nodebox.graphics.geometry import angle, distance, clamp, Bounds, INFINITE
from nodebox.graphics import \
    Layer, Color, Image, image, crop, rect, \
    Text, font, NORMAL, BOLD, CENTER, DEFAULT_FONT, install_font, \
    translate, rotate, \
    line, DASHED, DOTTED, \
    DEFAULT, HAND, TEXT, \
    LEFT, RIGHT, UP, DOWN, TAB, ENTER, BACKSPACE, CTRL, SHIFT, ALT

def _popdefault(dict, key, default=None):
    """ Pops the given key from the dictionary and returns its value (or default).
    """
    if key in dict: 
        return dict.pop(key)
    return default
    
def _find(match=lambda item: False, list=[]):
    """ Returns the first item in the list for which match(item)=True, or None.
    """
    for item in list:
        if match(item): return item

#=====================================================================================================

#--- Theme -------------------------------------------------------------------------------------------

class Theme(dict):
    
    def __init__(self, path, **kwargs):
        """ A theme defines the source images for controls and font settings for labels.
            A theme is loaded from a given folder path (containing PNG images and TTF font files).
            The default theme is in nodebox/graphics/gui/theme/
            Copy this folder and modify it to create a custom theme.
        """
        images = glob(os.path.join(path, "*.png"))
        images = [(os.path.basename(os.path.splitext(f)[0]), f) for f in images]
        fonts  = glob(os.path.join(path, "*.ttf"))
        fonts  = [(os.path.basename(os.path.splitext(f)[0]), install_font(f)) for f in fonts]
        fonts  = [f[0] for f in fonts if f[1]] # Filename is assumed to be fontname.
        dict.__init__(self, images)
        self["fonts"]      = fonts
        self["fontname"]   = kwargs.get("fontname", fonts and fonts[-1] or DEFAULT_FONT)
        self["fontsize"]   = kwargs.get("fontsize", 10)
        self["fontweight"] = kwargs.get("fontweight", NORMAL)
        self["text"]       = kwargs.get("text", Color(1.0))

theme = Theme(os.path.join(os.path.dirname(__file__), "theme")) 

#=====================================================================================================

#--- Control -----------------------------------------------------------------------------------------

class Control(Layer):
    
    def __init__(self, x=0, y=0, id=None, **kwargs):
        """ Base class for GUI controls.
            The Control class inherits from Layer so it must be appended to the canvas (or a container)
            to receive events and get drawn.
            An id can be given to uniquely identify the control.
            If the control is part of a Panel, it can be retrieved with Panel.control_id.
        """
        Layer.__init__(self, x=x, y=y, **kwargs)
        self.id        = id
        self.src       = {}    # Collection of source images.
        self.enabled   = True  # Enable event listener.
        self.duration  = 0     # Disable tweening.
        self._controls = {}    # Lazy index of (id, control) children, see nested().
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
        # Fire Control.on_mouse_doubleclick() when mouse is pressed twice in same location.
        # Subclasses need to call this method in their overridden on_mouse_press().
        if  self._press and \
        abs(self._press[0] - mouse.x) < 2 and \
        abs(self._press[1] - mouse.y) < 2 and \
            self._press[2] == mouse.button and \
            self._press[3] == mouse.modifiers and \
            self._press[4] - time() > -0.4:
            self._press = None
            self.on_mouse_doubleclick(mouse)
        self._press = (mouse.x, mouse.y, mouse.button, mouse.modifiers, time())
        
    def on_mouse_doubleclick(self, mouse):
        pass
        
    def on_key_press(self, keys):
        for control in self: 
            control.on_key_press(keys)
    def on_key_release(self, keys):
        for control in self: 
            control.on_key_release(keys)
    
    def on_action(self):
        """ Override this method with a custom action.
        """
        pass
        
    def reset(self):
        pass

    def _draw(self):
        Layer._draw(self)
    
    # Control._pack() is called internally to layout child controls.
    # This should not happen in Control.update(), which is called every frame.
    def _pack(self):
        pass

    # With transformed=True, expensive matrix transformations are done.
    # Turn off, controls are not meant to be rotated or scaled.        
    def layer_at(self, x, y, clipped=False, enabled=False, transformed=True, _covered=False):
        return Layer.layer_at(self, x, y, clipped, enabled, False, _covered)

    def origin(self, x=None, y=None, relative=False): 
        return Layer.origin(self, x, y, relative)       
    def rotate(self, angle): 
        pass
    def scale(self, f): 
        pass
    
    def __getattr__(self, k):
        # Yields the property with the given name, or
        # yields the child control with the given id.
        if k in self.__dict__: 
            return self.__dict__[k]
        ctrl = nested(self, k)
        if ctrl is not None:
            return ctrl
        raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__.__name__, k)
        
    def __repr__(self):
        return "%s(id=%s%s)" % (
            self.__class__.__name__,
            repr(self.id),
            hasattr(self, "value") and ", value="+repr(self.value) or ""
        )
        
def nested(control, id):
    """ Returns the child Control with the given id, or None.
        Also searches all child Layout containers.
    """
    # First check the Control._controls cache (=> 10x faster).
    # Also check if the control's id changed after it was cached (however unlikely).
    # If so, the cached entry is no longer valid.
    if id in control._controls:
        ctrl = control._controls[id]
        if ctrl.id == id:
            return ctrl
        del control._controls[id]
    # Nothing in the cache.
    # Traverse all child Control and Layout objects.
    m = None
    for ctrl in control:
        if ctrl.__dict__.get("id") == id:
            m = ctrl; break
        if isinstance(ctrl, Layout):
            m = nested(ctrl, id)
            if m is not None: 
                break
    # If a control was found, cache it.
    if m is not None:
        control._controls[id] = m
    return m

#=====================================================================================================

#--- Label -------------------------------------------------------------------------------------------

class Label(Control):
    
    def __init__(self, caption, x=0, y=0, width=None, height=None, id=None, **kwargs):
        """ A label displaying the given caption, centered in the label's (width, height)-box.
            The label does not receive any events.
            Optional parameters can include fill, font, fontsize, fontweight.
        """
        txt = Text(caption, **{
               "fill" : _popdefault(kwargs, "fill", theme["text"]),
               "font" : _popdefault(kwargs, "font", theme["fontname"]),
           "fontsize" : _popdefault(kwargs, "fontsize", theme["fontsize"]),
         "fontweight" : _popdefault(kwargs, "fontweight", theme["fontweight"]),
         "lineheight" : 1,
              "align" : CENTER
        })
        kwargs.setdefault("width", txt.metrics[0])
        kwargs.setdefault("height", txt.metrics[1])
        Control.__init__(self, x=x, y=y, id=id, **kwargs)
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
    def font(self):
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
    
    def __init__(self, caption="", action=None, x=0, y=0, width=125, id=None, **kwargs):
        """ A clickable button that will fire Button.on_action() when clicked.
            The action handler can be defined in a subclass, or given as a function.
        """
        Control.__init__(self, x=x, y=y, width=width, id=id, **kwargs)
        img, w = Image(theme["button"]), 20
        self.src = {
            "face" : crop(img, w, 0, 1, img.height),
            "cap1" : crop(img, 0, 0, w, img.height),
            "cap2" : crop(img, img.width-w, 0, w, img.height),
        }
        if action:
            # Override the Button.on_action() method from the given function.
            self.set_method(action, name="on_action")
        _popdefault(kwargs, "width")
        _popdefault(kwargs, "height")
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
    
    def __init__(self, action=None, x=0, y=0, id=None, **kwargs):
        """ A clickable button that will fire Action.on_action() when clicked.
            Actions display an icon instead of a text caption.
            Actions are meant to be used for interface management:
            e.g. closing or minimizing a panel, navigating to the next page, ...
        """
        Control.__init__(self, x=x, y=y, id=id, **kwargs)
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
    
    def __init__(self, action=None, x=0, y=0, id=None, **kwargs):
        """ An action that hides the parent control (e.g. a Panel) when pressed.
        """
        Action.__init__(self, action, x=x, y=y, id=id, **kwargs)
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
        clr = self.parent.pressed | self.pressed and (0.75, 0.75, 0.75) or (1.0, 1.0, 1.0)
        image(self.parent.src["handle"], 0, 0, color=clr)

class Slider(Control):
    
    def __init__(self, default=0.5, min=0.0, max=1.0, steps=100, x=0, y=0, width=125, id=None, **kwargs):
        """ A draggable slider that will fire Slider.on_action() when dragged.
            The slider's value can be retrieved with Slider.value.
        """
        Control.__init__(self, x=x, y=y, width=width, id=id, **kwargs)
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
        self.on_mouse_press(mouse)

#=====================================================================================================

#--- KNOB --------------------------------------------------------------------------------------------

class Knob(Control):
    
    def __init__(self, default=0, limit=True, x=0, y=0, id=None, **kwargs):
        """ A twistable knob that will fire Knob.on_action() when dragged.
            The knob's angle can be retrieved with Knob.value (in degrees, 0-360).
            With CTRL pressed, twists by a very small amount.
        """
        Control.__init__(self, x=x, y=y, id=id, **kwargs)
        self.default = default # Knob default angle.
        self.value   = default # Knob current angle.
        self._limit  = limit   # Constrain between 0-360 or scroll endlessly?
        self.src = {
            "face" : Image(theme["knob"]),
          "socket" : Image(theme["knob-socket"]),
        }
        self._pack()
        
    @property
    def relative(self):
        """ Yields the knob's angle as a relative number (0.0-1.0).
        """
        return self.value % 360 / 360.0

    def _pack(self):
        self._set_width(self.src["socket"].width)
        self._set_height(self.src["socket"].height)

    def reset(self):
        Control.reset(self)
        self.value = self.default

    def draw(self):
        translate(self.width/2, self.height/2)
        image(self.src["socket"], -self.width/2, -self.height/2)
        rotate(360-self.value)
        clr = self.pressed and (0.85, 0.85, 0.85) or (1.0, 1.0, 1.0)
        image(self.src["face"], -self.width/2, -self.height/2, color=clr)
        
    def on_mouse_press(self, mouse):
        self.value += mouse.dy * (CTRL in mouse.modifiers and 1 or 5)
        if self._limit:
            self.value %= 360
        self.on_action()
    
    def on_mouse_drag(self, mouse):
        self.on_mouse_press(mouse)

#=====================================================================================================

#--- FLAG --------------------------------------------------------------------------------------------

class Flag(Control):
    
    def __init__(self, default=False, x=0, y=0, id=None, **kwargs):
        """ A checkbox control that fires Flag.on_action() when checked.
            The checkbox value can be retrieved with Flag.value.
        """
        Control.__init__(self, x=x, y=y, id=id, **kwargs)
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

#--- Editable ----------------------------------------------------------------------------------------

EDITING = None
editing = lambda: EDITING

class Editable(Control):
    
    def __init__(self, value="", x=0, y=0, width=125, height=30, padding=(0,0), wrap=True, id=None, **kwargs):
        """ An editable text box.
            When clicked, it has the focus and can receive keyboard events.
            With wrap=True, several lines of text will wrap around the width.
            Optional parameters can include fill, font, fontsize, fontweight.
        """
        txt = Text(value or " ", **{
               "fill" : _popdefault(kwargs, "fill", Color(0,0.9)),
               "font" : _popdefault(kwargs, "font", theme["fontname"]),
           "fontsize" : _popdefault(kwargs, "fontsize", theme["fontsize"]),
         "fontweight" : _popdefault(kwargs, "fontweight", theme["fontweight"]),
         "lineheight" : _popdefault(kwargs, "lineheight", 1),
              "align" : LEFT
        })
        kwargs["width"]  = width
        kwargs["height"] = height
        Control.__init__(self, x=x, y=y, id=id, **kwargs)
        self.reserved = kwargs.get("reserved", [ENTER, TAB])
        self._padding = padding
        self._i       = 0     # Index of character on which the mouse is pressed.
        self._empty   = value == "" and True or False
        self._editor  = IncrementalTextLayout(txt._label.document, width, height, multiline=wrap)
        self._editor.content_valign = wrap and "top" or "center"
        self._editor.selection_background_color = (170, 200, 230, 255)
        self._editor.selection_color = txt._label.color
        self._editor.caret = Caret(self._editor)
        self._editor.caret.visible = False
        self._editing = False # When True, cursor is blinking and text can be edited.
        Editable._pack(self)  # On init, call Editable._pack(), not the derived Field._pack().
        
    def _pack(self):
        self._editor.x = self._padding[0]
        self._editor.y = self._padding[1]
        self._editor.width  = max(0, self.width  - self._padding[0] * 2)
        self._editor.height = max(0, self.height - self._padding[1] * 2)

    def _get_value(self):
        # IncrementalTextLayout in Pyglet 1.1.4 has a bug with empty strings.
        # We keep track of empty strings with Editable._empty to avoid this.
        return not self._empty and self._editor.document.text or u""
    def _set_value(self, string):
        self._editor.begin_update()
        self._editor.document.text = string or " "
        self._editor.end_update()
        self._empty = string == "" and True or False
        
    value = property(_get_value, _set_value)

    def _get_editing(self):
        return self._editing
    def _set_editing(self, b):
        self._editing = b
        self._editor.caret.visible = b
        global EDITING
        if b is False and EDITING == self:
            EDITING = None
        if b is True:
            EDITING = self
            # Cursor is blinking and text can be edited.
            # Visit all layers on the canvas.
            # Remove the caret from all other Editable controls.
            for layer in (self.root.canvas and self.root.canvas.layers or []):
                layer.traverse(visit=lambda layer: \
                    isinstance(layer, Editable) and layer != self and \
                        setattr(layer, "editing", False))
                        
    editing = property(_get_editing, _set_editing)

    @property
    def selection(self):
        # Yields a (start, stop)-tuple with the indices of the current selected text.
        return (self._editor.selection_start,
                self._editor.selection_end)
    
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
        i = self._i = self.index(mouse.x, mouse.y)
        self._editor.set_selection(0, 0)
        self.editing = True
        self._editor.caret.position = i
        Control.on_mouse_press(self, mouse)
        
    def on_mouse_release(self, mouse):
        if not self.dragged:
            self._editor.caret.position = self.index(mouse.x, mouse.y)
        Control.on_mouse_release(self, mouse)
        
    def on_mouse_drag(self, mouse):
        i = self.index(mouse.x, mouse.y)
        self._editor.selection_start = max(min(self._i, i), 0)
        self._editor.selection_end   = min(max(self._i, i), len(self.value))
        self._editor.caret.visible = False
        Control.on_mouse_drag(self, mouse)

    def on_mouse_doubleclick(self, mouse):
        # Select the word at the mouse position. 
        # Words are delimited by non-alphanumeric characters.
        i = self.index(mouse.x, mouse.y)
        delimiter = lambda ch: not (ch.isalpha() or ch.isdigit())
        if i  < len(self.value) and delimiter(self.value[i]):
            self._editor.set_selection(i, i+1)
        if i == len(self.value) and self.value != "" and delimiter(self.value[i-1]):
            self._editor.set_selection(i-1, i)
        a = _find(lambda (i,ch): delimiter(ch), enumerate(reversed(self.value[:i])))
        b = _find(lambda (i,ch): delimiter(ch), enumerate(self.value[i:]))
        a = a and i-a[0] or 0
        b = b and i+b[0] or len(self.value)
        self._editor.set_selection(a, b)

    def on_key_press(self, keys):
        if self._editing:
            self._editor.caret.visible = True
            i = self._editor.caret.position
            if   keys.code == LEFT:
                # The left arrow moves the text cursor to the left.
                self._editor.caret.position = max(i-1, 0)
            elif keys.code == RIGHT:
                # The right arrow moves the text cursor to the right.
                self._editor.caret.position = min(i+1, len(self.value))
            elif keys.code in (UP, DOWN):
                # The up arrows moves the text cursor to the previous line.
                # The down arrows moves the text cursor to the next line.
                y = keys.code == UP and -1 or +1
                n = self._editor.get_line_count()
                i = self._editor.get_position_on_line(
                    max(self._editor.get_line_from_position(i)+y, 0),
                        self._editor.get_point_from_position(i)[0])
                self._editor.caret.position = i
            elif keys.code == TAB and TAB in self.reserved:
                # The tab key navigates away from the control.
                self._editor.caret.position = 0
                self.editing = False
            elif keys.code == ENTER and ENTER in self.reserved:
                # The enter key executes on_action() and navigates away from the control.
                self._editor.caret.position = 0
                self.editing = False
                self.on_action()
            elif keys.code == BACKSPACE and self.selected:
                # The backspace key removes the current text selection.
                self.value = self.value[:self.selection[0]] + self.value[self.selection[1]:]
                self._editor.caret.position = max(self.selection[0], 0)
            elif keys.code == BACKSPACE and i > 0:
                # The backspace key removes the character at the text cursor.
                self.value = self.value[:i-1] + self.value[i:]
                self._editor.caret.position = max(i-1, 0)
            elif keys.char:
                if self.selected:
                    # Typing replaces any text currently selected.
                    self.value = self.value[:self.selection[0]] + self.value[self.selection[1]:]
                    self._editor.caret.position = i = max(self.selection[0], 0)
                ch = keys.char
                ch = ch.replace("\r", "\n\r")
                self.value = self.value[:i] + ch + self.value[i:]
                self._editor.caret.position = min(i+1, len(self.value))
            self._editor.set_selection(0, 0)
    
    def draw(self):
        self._editor.draw()

#--- Field -------------------------------------------------------------------------------------------

class Field(Editable):
    
    def __init__(self, value="", hint="", action=None, x=0, y=0, width=125, padding=5, id=None, **kwargs):
        """ A single-line text input field.
            The string value can be retrieved with Field.value.
        """
        Editable.__init__(self, value, x=x, y=y, width=width, padding=(padding,0), wrap=False, id=id, **kwargs)
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
        
    hint = property(_get_hint, _set_hint)

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
        self[0].hidden = self.editing or self.value != ""
    
    def draw(self):
        im1, im2, im3 = self.src["cap1"], self.src["cap2"], self.src["face"]
        image(im1, 0, 0, height=self.height)
        image(im2, x=self.width-im2.width, height=self.height)
        image(im3, x=im1.width, width=self.width-im1.width-im2.width, height=self.height)
        Editable.draw(self)

#=====================================================================================================

#--- Rulers ------------------------------------------------------------------------------------------

class Rulers(Control):
    
    def __init__(self, step=10, interval=5, crosshair=False, fill=(0,0,0,1)):
        """ A horizontal and vertical ruler displaying the width/height of the parent at intervals.
            A measurement line is drawn at each step(e.g. at 10 20 30...)
            A label with the value is drawn at each interval (e.g. 50 | | | | 100 | | | | 150).
        """
        Control.__init__(self, x=0, y=0)
        self.enabled   = False
        self.step      = step
        self.interval  = interval
        self.crosshair = crosshair
        self._fill     = fill
        self._dirty    = False
        self._markers  = {}
        self._pack()
    
    def _get_step(self):
        return self._step
    def _set_step(self, v):
        self._step = round(v)
        self._dirty = True
        
    step = property(_get_step, _set_step)
    
    def _get_interval(self):
        return self._interval
    def _set_interval(self, v):
        self._interval = round(v)
        self._dirty = True
        
    interval = property(_get_interval, _set_interval)
    
    def _pack(self):
        # Cache Text objects for the measurement markers.
        # This happens whenever the canvas resizes, or the step or interval changes.
        # This will raise an error if the parent's width or height is None (infinite).
        p = self.parent or self.canvas
        if p and (self._dirty or self.width != p.width or self.height != p.height):
            self._dirty = False
            self._set_width(p.width)
            self._set_height(p.height)
            for i in range(int(round(max(self.width, self.height) / self._step))):
                if i % self._interval == 0:
                    self._markers.setdefault(i*self._step,
                        Text(str(int(round(i*self._step))), 
                            fontname = theme["fontname"],
                            fontsize = theme["fontsize"] * 0.6,
                                fill = self._fill))
                            
    def update(self):
        self._pack()
    
    def draw(self):
        length = 5
        # Draw the horizontal ruler.
        for i in range(1, int(round(self.height / self._step))):
            v, mark = i*self._step, i%self.interval==0
            line(0, v, mark and length*3 or length, v, 
                     stroke = self._fill, 
                strokewidth = 0.5)
            if mark:
                self._markers[v].draw(length*3-self._markers[v].metrics[0], v+2)
        # Draw the vertical ruler.
        for i in range(1, int(round(self.width / self._step))):
            v, mark = i*self._step, i%self.interval==0
            line(v, 0, v, mark and length*3 or length, 
                     stroke = self._fill, 
                strokewidth = 0.5)
            if mark:
                self._markers[v].draw(v+2, length*3-self._markers[v].fontsize)
        # Draw the crosshair.
        if self.crosshair:
            line(0, self.canvas.mouse.y, self.width, self.canvas.mouse.y, 
                     stroke = self._fill, 
                strokewidth = 0.5, 
                strokestyle = DOTTED)
            line(self.canvas.mouse.x, 0, self.canvas.mouse.x, self.height, 
                     stroke = self._fill, 
                strokewidth = 0.5, 
                strokestyle = DOTTED)

#=====================================================================================================

#--- PANEL -------------------------------------------------------------------------------------------    

class Panel(Control):
    
    def __init__(self, caption="", fixed=False, modal=True, x=0, y=0, width=175, height=250, **kwargs):
        """ A panel containing other controls that can be dragged when Panel.fixed=False.
            Controls or (Layout groups) can be added with Panel.append().
        """
        Control.__init__(self, x=x, y=y, width=max(width,60), height=max(height,60), **kwargs)
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
        _popdefault(kwargs, "width")
        _popdefault(kwargs, "height")
        self.append(Label(caption, **kwargs))
        self.append(Close())
        self.fixed = fixed # Draggable?
        self.modal = modal # Closeable?
        self._pack()

    def _get_caption(self):
        return self._caption.text
    def _set_caption(self, str):
        self._caption.text = str
        self._pack()
        
    caption = property(_get_caption, _set_caption)

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
        for control in controls: 
            self.append(control)

    def _pack(self):
        # Center the caption in the label's header.
        # Position the close button in the top right corner.
        self[0].x = 0.5 * (self.width - self[0].width)
        self[0].y = self.height - self.src["top"].height + 0.5 * (self.src["top"].height - self[0].height)
        self[1].x = self.width - self[1].width - 4
        self[1].y = self.height - self[1].height - 2
        
    def pack(self, padding=20):
        """ Resizes the panel to the most compact size,
            based on the position and size of the controls in the panel.
        """
        def _visit(control):
            if control not in (self, self[0], self[1]):
                self._b = self._b and self._b.union(control.bounds) or control.bounds
        self._b = None
        self.traverse(_visit)
        for control in self.controls:
            control.x += padding + self.x - self._b.x
            control.y += padding + self.y - self._b.y
        self._set_width( padding + self._b.width  + padding)
        self._set_height(padding + self._b.height + padding + self.src["top"].height)
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
        self._dragged = not self.fixed and mouse.y > self.y+self.height-self.src["top"].height

    def on_mouse_drag(self, mouse):
        if self._dragged and not self.fixed:
            self.x += mouse.dx
            self.y += mouse.dy
        self.dragged = self._dragged
    
    def open(self):
        self.hidden = False
    def close(self):
        self.hidden = True

class Dock(Panel):
    
    def __init__(self, anchor=LEFT, caption="", fixed=True, modal=True, **kwargs):
        """ A panel attached to the edge of the canvas (LEFT or RIGHT), extending the full height.
            With fixed=False, it can be snapped from the edge and dragged as a normal panel.
        """
        kwargs.setdefault("x", anchor==RIGHT and INFINITE or 0)
        kwargs.setdefault("y", 0)
        Panel.__init__(self, caption=caption, fixed=fixed, modal=modal, **kwargs)
        self.anchor = anchor
        self.snap   = 1
    
    def update(self):
        Panel.update(self)
        if self.canvas is not None:
            if self.anchor == LEFT and self.x < self.snap:
                if self.dragged and self.x == 0:
                    # Stop drag once snapped to the edge.
                    self._dragged = False
                self.x = 0
                self.y = self.canvas.height - self.height
            if self.anchor == RIGHT and self.x > self.canvas.width-self.width - self.snap:
                if self.dragged and self.x == self.canvas.width-self.width:
                    self._dragged = False
                self.x = self.canvas.width  - self.width
                self.y = self.canvas.height - self.height
            
    def draw(self):
        im1, im2 = self.src["top"], self.src["face"]
        if self.canvas is not None and \
          (self.anchor == LEFT  and self.x == 0) or \
          (self.anchor == RIGHT and self.x == self.canvas.width-self.width):
            image(im1, 0, self.height-im1.height, width=self.width)
            image(im2, 0, -self.canvas.height+self.height, width=self.width, height=self.canvas.height-im1.height)
        else:
            Panel.draw(self)

#=====================================================================================================

#--- Layout ------------------------------------------------------------------------------------------

class Layout(Layer):
    
    def __init__(self, x=0, y=0, **kwargs):
        """ A group of controls with a specific layout.
            Controls can be added with Layout.append().
            The layout will be applied when Layout.apply() is called.
            This happens automatically if a layout is appended to a Panel.
        """
        
        kwargs["width"]  = 0
        kwargs["height"] = 0
        Layer.__init__(self, x=x, y=y, **kwargs)
        self._controls = {} # Lazy cache of (id, control)-children, see nested().

    def insert(self, i, control):
        if isinstance(control, Layout):
            control.apply() # If the control is actually a Layout, apply it.
        Layer.insert(self, i, control)
        
    def append(self, control):
        self.insert(len(self), control)
    def extend(self, controls):
        for control in controls: 
            self.append(control)

    def on_key_press(self, keys):
        for control in self: 
            control.on_key_press(keys)
    def on_key_release(self, keys):
        for control in self: 
            control.on_key_release(keys)
    
    def __getattr__(self, k):
        # Yields the property with the given name, or
        # yields the child control with the given id.
        if k in self.__dict__: 
            return self.__dict__[k]
        ctrl = nested(self, k)
        if ctrl is not None:
            return ctrl
        raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__.__name__, k)

    def apply(self, spacing=0):
        """ Adjusts the position and size of the controls to match the layout.
        """
        pass
        
    def __repr__(self):
        return "Layout(type=%s)" % repr(self.__class__.__name__.lower())
    
    # Debug mode:
    #def draw(self):
    #    rect(0, 0, self.width, self.height, fill=None, stroke=(1,1,1,0.5), strokestyle="dotted")

#--- Layout: Labeled ----------------------------------------------------------------------------------

class Labeled(Layout):

    def __init__(self, controls=[], x=0, y=0):
        """ A layout where each control has an associated text label.
        """
        Layout.__init__(self, x=x, y=y)
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

#--- Layout: Rows ------------------------------------------------------------------------------------

class Rows(Labeled):

    def __init__(self, controls=[], x=0, y=0, width=125):
        """ A layout where each control appears on a new line.
            Each control has an associated text caption, displayed to the left of the control.
            The given width defines the desired width for each control.
        """
        Labeled.__init__(self, controls, x=x, y=y)
        self._maxwidth = width

    def apply(self, spacing=10):
        """ Adjusts the position and width of all the controls in the layout:
            - each control is placed next to its caption, with spacing in between,
            - each caption is aligned to the right, and centered vertically,
            - the width of all Label, Button, Slider, Field controls is evened out.
        """
        mw = self._maxwidth
        for control in self.controls:
            if isinstance(control, Layout):
                # Child containers in the layout can be wider than the desired width.
                # adjusting mw at the start will controls wider to line out with the total width,
                # adjusting it at the end would just ensure that the layout is wide enough.
                mw = max(self._maxwidth, control.width)
        w1 = max([caption.width for caption in self.captions])
        w2 = max([control.width for control in self.controls])
        dx = 0
        dy = 0
        for caption, control in reversed(zip(self.captions, self.controls)):
            caption.x = dx + w1 - caption.width                      # halign right.
            control.x = dx + w1 + (w1>0 and spacing)
            caption.y = dy + 0.5 * (control.height - caption.height) # valign center.
            control.y = dy
            if isinstance(control, Layout) and control.height > caption.height * 2:
                caption.y = dy + control.height - caption.height     # valign top.
            if isinstance(control, (Label, Button, Slider, Field)):
                control._set_width(mw)
                control._pack()
            dy += max(caption.height, control.height, 10) + spacing
        self.width  = w1 + w2 + (w1>0 and spacing)
        self.height = dy - spacing

TOP, CENTER = "top", "center"

class Row(Labeled):

    def __init__(self, controls=[], x=0, y=0, width=125, align=CENTER):
        """ A layout where each control appears in a new column.
            Each control has an associated text caption, displayed on top of the control.
            The given width defines the desired width for each control.
        """
        Labeled.__init__(self, controls, x=x, y=y)
        self._maxwidth = width
        self._align    = align

    def apply(self, spacing=10):
        """ Adjusts the position and width of all the controls in the layout:
            - each control is placed centrally below its caption, with spacing in between,
            - the width of all Label, Button, Slider, Field controls is evened out.
        """
        mw = self._maxwidth
        da = self._align==TOP and 1.0 or 0.5
        h1 = max([control.height for control in self.controls])
        h2 = max([caption.height for caption in self.captions])
        dx = 0
        dy = 0
        for caption, control in zip(self.captions, self.controls):
            caption.x = dx + 0.5 * max(control.width - caption.width, 0) # halign center
            control.x = dx + 0.5 * max(caption.width - control.width, 0) # halign center
            caption.y = dy + h1 + (h2>0 and spacing)                 
            control.y = dy + da * (h1 - control.height)                  # valign center
            if isinstance(control, (Label, Button, Slider, Field)):
                control._set_width(mw)
                control._pack()
            dx += max(caption.width, control.width, 10) + spacing
        self.width = dx - spacing
        self.height = h1 + h2 + (h2>0 and spacing)
