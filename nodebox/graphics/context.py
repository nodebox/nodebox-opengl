#=== CONTEXT =========================================================================================
# 2D NodeBox API in OpenGL.
# Authors: Tom De Smedt, Frederik De Bleser
# License: BSD (see LICENSE.txt for details).
# Copyright (c) 2008 City In A Bottle (cityinabottle.org)
# http://cityinabottle.org/nodebox

# All graphics are drawn directly to the screen.
# No scenegraph is kept for obvious performance reasons (therefore, no canvas._grobs as in NodeBox).

# Debugging must be switched on or of before other modules are imported.
import pyglet
pyglet.options['debug_gl'] = False

from pyglet.gl    import *
from pyglet.image import Texture
from math         import cos, sin, radians, pi, floor
from time         import time
from random       import seed, choice, shuffle, random as rnd
from new          import instancemethod
from glob         import glob
from os           import path, remove
from sys          import getrefcount
from StringIO     import StringIO
from hashlib      import md5
from types        import FunctionType
from datetime     import datetime

import geometry

#import bezier
# Do this at the end, when we have defined BezierPath, which is needed in the bezier module.

#import shader
# Do this when we have defined texture() and image(), which are needed in the shader module.

# OpenGL version, e.g. "2.0 NVIDIA-1.5.48".
OPENGL = pyglet.gl.gl_info.get_version()

#=====================================================================================================

#--- CACHING -----------------------------------------------------------------------------------------
# OpenGL Display Lists offer a simple way to precompile batches of OpenGL commands.
# The drawback is that the commands, once compiled, can't be modified.

def precompile(function, *args, **kwargs):
    """ Creates an OpenGL Display List from the OpenGL commands in the given function.
        A Display List will precompile the commands and (if possible) store them in graphics memory.
        Returns an id which can be used with precompiled() to execute the cached commands.
    """
    id = glGenLists(1)
    glNewList(id, GL_COMPILE)
    function(*args, **kwargs)
    glEndList()
    return id
        
def precompiled(id):
    """ Executes the Display List program with the given id.
    """
    glCallList(id)
        
def flush(id):
    """ Removes the Display List program with the given id from memory.
    """
    if id is not None:
        glDeleteLists(id, 1)

#=====================================================================================================

#--- COLOR -------------------------------------------------------------------------------------------

RGB = "RGB"
HSB = "HSB"
XYZ = "XYZ"
LAB = "LAB"

_background  = None    # Current state background color.
_fill        = None    # Current state fill color.
_stroke      = None    # Current state stroke color.
_strokewidth = 1       # Current state strokewidth.
_strokestyle = "solid" # Current state strokestyle.
_alpha       = 1       # Current state alpha transparency.

class Color(list):

    def __init__(self, *args, **kwargs):
        """ A color with R,G,B,A channels, with channel values ranging between 0.0-1.0.
            Either takes four parameters (R,G,B,A), three parameters (R,G,B),
            two parameters (grayscale and alpha) or one parameter (grayscale or Color object).
            An optional base=1.0 parameter defines the range of the given parameters.
            An optional colorspace=RGB defines the color space of the given parameters.
        """
        # Values are supplied as a tuple.
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            args = args[0]
        # R, G, B and A.
        if len(args) == 4:
            r, g, b, a = args[0], args[1], args[2], args[3]
        # R, G and B.
        elif len(args) == 3:
            r, g, b, a = args[0], args[1], args[2], 1
        # Two values, grayscale and alpha.
        elif len(args) == 2:
            r, g, b, a = args[0], args[0], args[0], args[1]
        # One value, another color object.
        elif len(args) == 1 and isinstance(args[0], Color):
            r, g, b, a = args[0].r, args[0].g, args[0].b, args[0].a
        # One value, None.
        elif len(args) == 1 and args[0] is None:
            r, g, b, a = 0, 0, 0, 0
        # One value, grayscale.
        elif len(args) == 1:
            r, g, b, a = args[0], args[0], args[0], 1
        # No value, transparent black.
        elif len(args):
            r, g, b, a = 0, 0, 0, 0
        # Transform to base 1:
        base = float(kwargs.get("base", 1.0))
        if base != 1:
            r, g, b, a = [ch/base for ch in r, g, b, a]
        # Transform to color space RGB:
        colorspace = kwargs.get("colorspace")
        if colorspace and colorspace != RGB:
            if colorspace == HSB: r, g, b = hsb_to_rgb(r, g, b)
            if colorspace == XYZ: r, g, b = xyz_to_rgb(r, g, b)
            if colorspace == LAB: r, g, b = lab_to_rgb(r, g, b)
        list.__init__(self, [r, g, b, a])
        self._dirty = False

    def __setitem__(self, i, v):
        list.__setitem__(self, i, v)
        self._dirty = True

    def _get_r(self): return self[0]
    def _get_g(self): return self[1]
    def _get_b(self): return self[2]
    def _get_a(self): return self[3]
    
    def _set_r(self, v): self[0] = v
    def _set_g(self, v): self[1] = v
    def _set_b(self, v): self[2] = v
    def _set_a(self, v): self[3] = v
    
    r = red   = property(_get_r, _set_r)
    g = green = property(_get_g, _set_g)
    b = blue  = property(_get_b, _set_b)
    a = alpha = property(_get_a, _set_a)
    
    def _get_rgb(self):
        return self[0], self[1], self[2]
    def _set_rgb(self, (r,g,b)):
        self[0] = r
        self[1] = g
        self[2] = b
        
    rgb = property(_get_rgb, _set_rgb)
    
    def _get_rgba(self):
        return self[0], self[1], self[2], self[3]
    def _set_rgba(self, (r,g,b,a)):
        self[0] = r
        self[1] = g
        self[2] = b
        self[3] = a
        
    rgba = property(_get_rgba, _set_rgba)

    def copy(self):
        return Color(self)

    def _apply(self):
        glColor4f(self[0], self[1], self[2], self[3] * _alpha)

    def __repr__(self):
        return "Color(%.3f, %.3f, %.3f, %.3f)" % \
            (self[0], self[1], self[2], self[3])
            
    def __eq__(self, clr):
        if not isinstance(clr, Color): return False
        return self[0] == clr[0] \
           and self[1] == clr[1] \
           and self[2] == clr[2] \
           and self[3] == clr[3]
    
    def __ne__(self, clr):
        return not self.__eq__(clr)
    
    def map(self, base=1.0, colorspace=RGB):
        """ Returns a list of R,G,B,A values mapped to the given base,
            e.g. from 0-255 instead of 0.0-1.0 which is useful for setting image pixels.
            Other values than RGBA can be obtained by setting the colorspace (RGB/HSB/XYZ/LAB).
        """
        r, g, b, a = self
        if colorspace != RGB:
            if colorspace == HSB: r, g, b = rgb_to_hsb(r, g, b)
            if colorspace == XYZ: r, g, b = rgb_to_xyz(r, g, b)
            if colorspace == LAB: r, g, b = rgb_to_lab(r, g, b)
        if base != 1:
            r, g, b, a = [ch*base for ch in r, g, b, a]
        if base != 1 and isinstance(base, int):
            r, g, b, a = [int(ch) for ch in r, g, b, a]
        return r, g, b, a
    
    def blend(self, clr, t=0.5, colorspace=RGB):
        """ Returns a new color between the two colors.
            Parameter t is the amount to interpolate between the two colors 
            (0.0 equals the first color, 0.5 is half-way in between, etc.)
            Blending in CIE-LAB colorspace avoids "muddy" colors in the middle of the blend.
        """
        ch = zip(self.map(1, colorspace)[:3], clr.map(1, colorspace)[:3])
        r, g, b = [geometry.lerp(a, b, t) for a, b in ch]
        a = geometry.lerp(self.a, len(clr)==4 and clr[3] or 1, t)
        return Color(r, g, b, a, colorspace=colorspace)
        
    def rotate(self, angle):
        """ Returns a new color with it's hue rotated on the RYB color wheel.
        """
        h, s, b = rgb_to_hsb(*self[:3])
        h, s, b = rotate_ryb(h, s, b, angle)
        return Color(h, s, b, self.a, colorspace=HSB)

color = Color

def background(*args, **kwargs):
    """ Sets the current background color.
    """
    global _background
    if args:
        _background = Color(*args, **kwargs)
        xywh = (GLint*4)(); glGetIntegerv(GL_VIEWPORT, xywh); x,y,w,h = xywh
        rect(x, y, w, h, fill=_background, stroke=None)   
    return _background

def fill(*args, **kwargs):
    """ Sets the current fill color for drawing primitives and paths.
    """
    global _fill
    if args:
        _fill = Color(*args, **kwargs)
    return _fill

fill(0) # The default fill is black.

def stroke(*args, **kwargs):
    """ Sets the current stroke color.
    """
    global _stroke
    if args:
        _stroke = Color(*args, **kwargs)
    return _stroke

def nofill():
    """ No current fill color.
    """
    global _fill
    _fill = None

def nostroke():
    """ No current stroke color.
    """
    global _stroke
    _stroke = None

def strokewidth(width=None):
    """ Sets the outline stroke width.
    """
    # Note: strokewidth is clamped to integers (e.g. 0.2 => 1), 
    # but finer lines can be achieved visually with a transparent stroke.
    # Thicker strokewidth results in ugly (i.e. no) line caps.
    global _strokewidth
    if width is not None:
        _strokewidth = width
        glLineWidth(width)
    return _strokewidth

SOLID  = "solid"
DOTTED = "dotted"
DASHED = "dashed"

def strokestyle(style=None):
    """ Sets the outline stroke style (SOLID / DOTTED / DASHED).
    """
    global _strokestyle
    if style is not None and style != _strokestyle:
        _strokestyle = style
        glLineDash(style)
    return _strokestyle
    
def glLineDash(style):
    if style == SOLID:
        glDisable(GL_LINE_STIPPLE)
    elif style == DOTTED:
        glEnable(GL_LINE_STIPPLE); glLineStipple(0, 0x0101)
    elif style == DASHED:
        glEnable(GL_LINE_STIPPLE); glLineStipple(1, 0x000F)

def outputmode(mode=None):
    raise NotImplementedError

def colormode(mode=None, range=1.0):
    raise NotImplementedError

#--- COLOR SPACE -------------------------------------------------------------------------------------
# Transformations between RGB, HSB, CIE XYZ and CIE LAB color spaces.
# http://www.easyrgb.com/math.php

def rgb_to_hsb(r, g, b):
    """ Converts the given R,G,B values to H,S,B (between 0.0-1.0).
    """
    h, s, v = 0, 0, max(r, g, b)
    d = v - min(r, g, b)
    if v != 0:
        s = d / float(v)
    if s != 0:
        if   r == v: h = 0 + (g-b) / d
        elif g == v: h = 2 + (b-r) / d
        else       : h = 4 + (r-g) / d
    h = h / 6.0 % 1
    return h, s, v

def hsb_to_rgb(h, s, v):
    """ Converts the given H,S,B color values to R,G,B (between 0.0-1.0).
    """
    if s == 0: 
        return v, v, v
    h = h % 1 * 6.0
    i = floor(h)
    f = h - i
    x = v * (1-s)
    y = v * (1-s * f)
    z = v * (1-s * (1-f))
    if i > 4:
        return v, x, y
    return [(v,z,x), (y,v,x), (x,v,z), (x,y,v), (z,x,v)][int(i)]
    
def rgb_to_xyz(r, g, b):
    """ Converts the given R,G,B values to CIE X,Y,Z (between 0.0-1.0).
    """
    r, g, b = [ch > 0.04045 and ((ch+0.055) / 1.055) ** 2.4 or ch / 12.92 for ch in r, g, b]
    r, g, b = [ch * 100.0 for ch in r, g, b]
    r, g, b = ( # Observer = 2, Illuminant = D65
        r * 0.4124 + g * 0.3576 + b * 0.1805,
        r * 0.2126 + g * 0.7152 + b * 0.0722,
        r * 0.0193 + g * 0.1192 + b * 0.9505)
    return r/95.047, g/100.0, b/108.883

def xyz_to_rgb(x, y, z):
    """ Converts the given CIE X,Y,Z color values to R,G,B (between 0.0-1.0).
    """
    x, y, z = x*95.047, y*100.0, z*108.883
    x, y, z = [ch / 100.0 for ch in x, y, z]
    r = x *  3.2406 + y * -1.5372 + z * -0.4986
    g = x * -0.9689 + y *  1.8758 + z *  0.0415
    b = x * -0.0557 + y * -0.2040 + z *  1.0570
    r, g, b = [ch > 0.0031308 and 1.055 * ch**(1/2.4) - 0.055 or ch * 12.92 for ch in r, g, b]
    return r, g, b

def rgb_to_lab(r, g, b):
    """ Converts the given R,G,B values to CIE L,A,B (between 0.0-1.0).
    """
    x, y, z = rgb_to_xyz(r, g, b)
    x, y, z = [ch > 0.008856 and ch**(1/3.0) or (ch*7.787) + (16/116.0) for ch in x, y, z]
    l, a, b = y*116-16, 500*(x-y), 200*(y-z)
    l, a, b = l/100.0, (a+86)/(86+98), (b+108)/(108+94)
    return l, a, b
    
def lab_to_rgb(l, a, b):
    """ Converts the given CIE L,A,B color values to R,G,B (between 0.0-1.0).
    """
    l, a, b = l*100, a*(86+98)-86, b*(108+94)-108
    y = (l+16)/116.0
    x = y + a/500.0
    z = y - b/200.0
    x, y, z = [ch**3 > 0.008856 and ch**3 or (ch-16/116.0)/7.787 for ch in x, y, z]
    return xyz_to_rgb(x, y, z)

def luminance(r, g, b):
    """ Returns an indication (0.0-1.0) of how bright the color appears.
    """
    return (r*0.2125 + g*0.7154 + b+0.0721) * 0.5

def darker(clr, step=0.2):
    """ Returns a copy of the color with a darker brightness.
    """
    h, s, b = rgb_to_hsb(clr.r, clr.g, clr.b)
    r, g, b = hsb_to_rgb(h, s, max(0, b-step))
    return Color(r, g, b, len(clr)==4 and clr[3] or 1)

def lighter(clr, step=0.2):
    """ Returns a copy of the color with a lighter brightness.
    """
    h, s, b = rgb_to_hsb(clr.r, clr.g, clr.b)
    r, g, b = hsb_to_rgb(h, s, min(1, b+step))
    return Color(r, g, b, len(clr)==4 and clr[3] or 1)
    
darken, lighten = darker, lighter

#--- COLOR ROTATION ----------------------------------------------------------------------------------

# Approximation of the RYB color wheel.
# In HSB, colors hues range from 0 to 360, 
# but on the color wheel these values are not evenly distributed. 
# The second tuple value contains the actual value on the wheel (angle).
_colorwheel = [
    (  0,   0), ( 15,   8), ( 30,  17), ( 45,  26),
    ( 60,  34), ( 75,  41), ( 90,  48), (105,  54),
    (120,  60), (135,  81), (150, 103), (165, 123),
    (180, 138), (195, 155), (210, 171), (225, 187),
    (240, 204), (255, 219), (270, 234), (285, 251),
    (300, 267), (315, 282), (330, 298), (345, 329), (360, 360)
]

def rotate_ryb(h, s, b, angle=180):
    """ Rotates the given H,S,B color (0.0-1.0) on the RYB color wheel.
        The RYB colorwheel is not mathematically precise,
        but focuses on aesthetically pleasing complementary colors.
    """
    h = h*360 % 360
    # Find the location (angle) of the hue on the RYB color wheel.
    for i in range(len(_colorwheel)-1):
        (x0, y0), (x1, y1) = _colorwheel[i], _colorwheel[i+1]
        if y0 <= h <= y1:
            a = geometry.lerp(x0, x1, t=(h-y0)/(y1-y0))
            break
    # Rotate the angle and retrieve the hue.
    a = (a+angle) % 360
    for i in range(len(_colorwheel)-1):
        (x0, y0), (x1, y1) = _colorwheel[i], _colorwheel[i+1]
        if x0 <= a <= x1:
            h = geometry.lerp(y0, y1, t=(a-x0)/(x1-x0))
            break
    return h/360.0, s, b
    
def complement(clr):
    """ Returns the color opposite on the color wheel.
        The complementary color contrasts with the given color.
    """
    return clr.rotate(180)

def analog(clr, angle=20, d=0.1):
    """ Returns a random adjacent color on the color wheel.
        Analogous color schemes can often be found in nature.
    """
    h, s, b = rgb_to_hsb(*clr[:3])
    h, s, b = rotate_ryb(h, s, b, angle=random(-angle,angle))
    s *= 1 - random(-d,d)
    b *= 1 - random(-d,d)
    return Color(h, s, b, len(clr)==4 and clr[3] or 1, colorspace=HSB)

#--- COLOR MIXIN -------------------------------------------------------------------------------------
# Drawing commands like rect() have optional parameters fill and stroke to set the color directly.

def color_mixin(**kwargs):
    fill        = kwargs.get("fill", _fill)
    stroke      = kwargs.get("stroke", _stroke)
    strokewidth = kwargs.get("strokewidth", _strokewidth)
    strokestyle = kwargs.get("strokestyle", _strokestyle)
    return (fill, stroke, strokewidth, strokestyle)

#--- COLOR PLANE -------------------------------------------------------------------------------------
# Not part of the standard API but too convenient to leave out.

def colorplane(x, y, width, height, *a):
    """ Draws a rectangle that emits a different fill color from each corner.
        An optional number of colors can be given: 
        - four colors define top left, top right, bottom right and bottom left,
        - three colors define top left, top right and bottom,
        - two colors define top and bottom,
        - no colors assumes black top and white bottom gradient.
    """
    if len(a) == 2:
        # Top and bottom colors.
        clr1, clr2, clr3, clr4 = a[0], a[0], a[1], a[1]
    elif len(a) == 4:
        # Top left, top right, bottom right, bottom left.
        clr1, clr2, clr3, clr4 = a[0], a[1], a[2], a[3]
    elif len(a) == 3:
        # Top left, top right, bottom.
        clr1, clr2, clr3, clr4 = a[0], a[1], a[2], a[2]
    elif len(a) == 0:
        # Black top, white bottom.
        clr1 = clr2 = (0,0,0,1)
        clr3 = clr4 = (1,1,1,1)
    glPushMatrix()
    glTranslatef(x, y, 0)
    glScalef(width, height, 1)
    glBegin(GL_QUADS)
    glColor4f(clr1[0], clr1[1], clr1[2], clr1[3] * _alpha); glVertex2f(-0.0,  1.0)
    glColor4f(clr2[0], clr2[1], clr2[2], clr2[3] * _alpha); glVertex2f( 1.0,  1.0)
    glColor4f(clr3[0], clr3[1], clr3[2], clr3[3] * _alpha); glVertex2f( 1.0, -0.0)
    glColor4f(clr4[0], clr4[1], clr4[2], clr4[3] * _alpha); glVertex2f(-0.0, -0.0)
    glEnd()
    glPopMatrix()

#=====================================================================================================

#--- TRANSFORMATIONS ---------------------------------------------------------------------------------
# Unlike NodeBox, all transformations are CORNER-mode and originate from the bottom-left corner.

# Example: using Transform to get a transformed path.
# t = Transform()
# t.rotate(45)
# p = BezierPath()
# p.rect(10,10,100,70)
# p = t.transform_path(p)
# p.contains(x,y) # now we can check if the mouse is in the transformed shape.
Transform = geometry.AffineTransform

def push():
    """ Pushes the transformation state.
        Subsequent transformations (translate, rotate, scale) remain in effect until pop() is called.
    """
    glPushMatrix()

def pop():
    """ Pops the transformation state.
        This reverts the transformation to before the last push().
    """
    glPopMatrix()

def translate(x, y, z=0):
    """ By default, the origin of the layer or canvas is at the bottom left.
        This origin point will be moved by (x,y) pixels.
    """
    glTranslatef(round(x), round(y), round(z))

def rotate(degrees, axis=(0,0,1)):
    """ Rotates the transformation state, i.e. all subsequent drawing primitives are rotated.
        Rotations work incrementally:
        calling rotate(60) and rotate(30) sets the current rotation to 90.
    """
    glRotatef(degrees, *axis)

def scale(x, y=None, z=None):
    """ Scales the transformation state.
    """
    if y is None: 
        y = x
    if z is None: 
        z = 1
    glScalef(x, y, z)

def reset():
    """ Resets the transform state of the layer or canvas.
    """
    glLoadIdentity()

CORNER = "corner"
CENTER = "center"
def transform(mode=None):
    if mode == CENTER:
        raise NotImplementedError, "no center-mode transform"
    return CORNER
    
def skew(x, y):
    raise NotImplementedError

#=====================================================================================================

#--- DRAWING PRIMITIVES ------------------------------------------------------------------------------
# Drawing primitives: Point, line, rect, ellipse, arrow. star.
# The fill and stroke are two different shapes put on top of each other.

Point = geometry.Point

def line(x0, y0, x1, y1, **kwargs):
    """ Draws a straight line from x0, y0 to x1, y1 with the current stroke color and strokewidth.
    """
    fill, stroke, strokewidth, strokestyle = color_mixin(**kwargs)
    if stroke is not None and strokewidth > 0:
        glColor4f(stroke[0], stroke[1], stroke[2], stroke[3] * _alpha)
        glLineWidth(strokewidth)
        glLineDash(strokestyle)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x0, y0)
        glVertex2f(x1, y1)
        glEnd()

def rect(x, y, width, height, **kwargs):
    """ Draws a rectangle with the bottom left corner at x, y.
        The current stroke, strokewidth and fill color are applied.
    """
    fill, stroke, strokewidth, strokestyle = color_mixin(**kwargs)
    for i, clr in enumerate((fill, stroke)):
        if clr is not None and (i==0 or strokewidth > 0):
            if i == 1: 
                glLineWidth(strokewidth)
                glLineDash(strokestyle)
            glColor4f(clr[0], clr[1], clr[2], clr[3] * _alpha)
            # Note: this performs equally well as when using precompile().
            glBegin((GL_POLYGON, GL_LINE_LOOP)[i])
            glVertex2f(x, y)
            glVertex2f(x+width, y)
            glVertex2f(x+width, y+height)
            glVertex2f(x, y+height)
            glEnd()
            
def triangle(x1, y1, x2, y2, x3, y3, **kwargs):
    """ Draws the triangle created by connecting the three given points.
        The current stroke, strokewidth and fill color are applied.
    """
    fill, stroke, strokewidth, strokestyle = color_mixin(**kwargs)
    for i, clr in enumerate((fill, stroke)):
        if clr is not None and (i==0 or strokewidth > 0):
            if i == 1: 
                glLineWidth(strokewidth)
                glLineDash(strokestyle)
            glColor4f(clr[0], clr[1], clr[2], clr[3] * _alpha)
            # Note: this performs equally well as when using precompile().
            glBegin((GL_POLYGON, GL_LINE_LOOP)[i])
            glVertex2f(x1, y1)
            glVertex2f(x2, y2)
            glVertex2f(x3, y3)
            glEnd()

_ellipses = {}
ELLIPSE_SEGMENTS = 50
def ellipse(x, y, width, height, segments=ELLIPSE_SEGMENTS, **kwargs):
    """ Draws an ellipse with the center located at x, y.
        The current stroke, strokewidth and fill color are applied.
    """
    if not segments in _ellipses:
        # For the given amount of line segments, calculate the ellipse once.
        # Then reuse the cached ellipse by scaling it to the desired size.
        _ellipses[segments] = []
        for mode in (GL_POLYGON, GL_LINE_LOOP):
            _ellipses[segments].append(precompile(lambda:(
                glBegin(mode),
               [glVertex2f(cos(t)/2, sin(t)/2) for t in [2*pi*i/segments for i in range(segments)]],
                glEnd()
            )))
    fill, stroke, strokewidth, strokestyle = color_mixin(**kwargs)
    for i, clr in enumerate((fill, stroke)):
        if clr is not None and (i==0 or strokewidth > 0):
            if i == 1: 
                glLineWidth(strokewidth)
                glLineDash(strokestyle)
            glColor4f(clr[0], clr[1], clr[2], clr[3] * _alpha)
            glPushMatrix()
            glTranslatef(x, y, 0)
            glScalef(width, height, 1)
            glCallList(_ellipses[segments][i])
            glPopMatrix()

oval = ellipse # Backwards compatibility.

def arrow(x, y, width, **kwargs):
    """ Draws an arrow with its tip located at x, y.
        The current stroke, strokewidth and fill color are applied.
    """
    head = width * 0.4
    tail = width * 0.2
    fill, stroke, strokewidth, strokestyle = color_mixin(**kwargs)
    for i, clr in enumerate((fill, stroke)):
        if clr is not None and (i==0 or strokewidth > 0):
            if i == 1: 
                glLineWidth(strokewidth)
                glLineDash(strokestyle)
            glColor4f(clr[0], clr[1], clr[2], clr[3] * _alpha)
            # Note: this performs equally well as when using precompile().
            glBegin((GL_POLYGON, GL_LINE_LOOP)[i])
            glVertex2f(x, y)
            glVertex2f(x-head, y+head)
            glVertex2f(x-head, y+tail)
            glVertex2f(x-width, y+tail)
            glVertex2f(x-width, y-tail)
            glVertex2f(x-head, y-tail)
            glVertex2f(x-head, y-head)
            glVertex2f(x, y)
            glEnd()

def star(x, y, points=20, outer=100, inner=50, **kwargs):
    """ Draws a star with the given points, outer radius and inner radius.
        The current stroke, strokewidth and fill color are applied.
    """
    # GL_POLYGON only works with convex polygons,
    # so we use a BezierPath (which does tessellation for fill colors).
    p = BezierPath(**kwargs)
    p.moveto(x, y+outer)
    for i in range(0, int(2*points)+1):
        r = (outer, inner)[i%2]
        a = pi*i/points
        p.lineto(x+r*sin(a), y+r*cos(a))
    p.closepath()
    if kwargs.get("draw", True): 
        p.draw(**kwargs)
    return p

#=====================================================================================================

#--- BEZIER PATH -------------------------------------------------------------------------------------
# A BezierPath class with lineto(), curveto() and moveto() commands.
# It has all the path math functionality from NodeBox and a ray casting algorithm for contains().
# A number of caching mechanisms are used for performance:
# drawn vertices, segment lengths, path bounds, and a hit test area for BezierPath.contains().
# For optimal performance, the path should be created once (not every frame) and left unmodified.
# When points in the path are added, removed or modified, a _dirty flag is set.
# When dirty, the cache will be cleared and the new path recalculated.
# If the path is being drawn with a fill color, this means doing tessellation
# (i.e. additional math for finding out if parts overlap and punch a hole in the shape).

MOVETO  = "moveto"
LINETO  = "lineto"
CURVETO = "curveto"
CLOSE   = "close"

RELATIVE = "relative" # Number of straight lines to represent a curve = 20% of curve length.
RELATIVE_PRECISION = 0.2

class PathError(Exception): 
    pass
class NoCurrentPointForPath(Exception): 
    pass
class NoCurrentPath(Exception): 
    pass

class PathPoint(Point):
    
    def __init__(self, x=0, y=0):
        """ A control handle for PathElement.
        """
        self._x = x
        self._y = y
        self._dirty = False
    
    def _get_x(self): return self._x
    def _set_x(self, v): 
        self._x = v
        self._dirty = True

    def _get_y(self): return self._y
    def _set_y(self, v):
        self._y = v
        self._dirty = True
        
    x = property(_get_x, _set_x)
    y = property(_get_y, _set_y)
    
    def copy(self, parent=None):
        return PathPoint(self._x, self._y)

class PathElement(object):
    
    def __init__(self, cmd=None, pts=None):
        """ A point in the path, optionally with control handles:
            - MOVETO  : the list of points contains a single (x,y)-tuple.
            - LINETO  : the list of points contains a single (x,y)-tuple.
            - CURVETO : the list of points contains (vx1,vy1), (vx2,vy2), (x,y) tuples.
            - CLOSETO : no points.
        """
        if cmd == MOVETO \
        or cmd == LINETO:
            pt, h1, h2 = pts[0], pts[0], pts[0]
        elif cmd == CURVETO:
            pt, h1, h2 = pts[2], pts[0], pts[1]
        else:
            pt, h1, h2 = (0,0), (0,0), (0,0)
        self._cmd    = cmd
        self._x      = pt[0]
        self._y      = pt[1]
        self._ctrl1  = PathPoint(h1[0], h1[1])
        self._ctrl2  = PathPoint(h2[0], h2[1])
        self.__dirty = False

    def _get_dirty(self):
        return self.__dirty \
            or self.ctrl1._dirty \
            or self.ctrl2._dirty
            
    def _set_dirty(self, b):
        self.__dirty = b
        self.ctrl1._dirty = b
        self.ctrl2._dirty = b
        
    _dirty = property(_get_dirty, _set_dirty)

    @property
    def cmd(self):
        return self._cmd

    def _get_x(self): return self._x
    def _set_x(self, v): 
        self._x = v
        self.__dirty = True
        
    def _get_y(self): return self._y
    def _set_y(self, v): 
        self._y = v
        self.__dirty = True
        
    x = property(_get_x, _set_x)
    y = property(_get_y, _set_y)

    def _get_xy(self):
        return (self.x, self.y)
    def _set_xy(self, (x,y)):
        self.x = x
        self.y = y
        
    xy = property(_get_xy, _set_xy)

    # Handle 1 describes now the curve from the previous point started.
    def _get_ctrl1(self): return self._ctrl1
    def _set_ctrl1(self, v):
        self._ctrl1 = PathPoint(v.x, v.y)
        self.__dirty = True

    # Handle 2 describes how the curve from the previous point arrives in this point.
    def _get_ctrl2(self): return self._ctrl2
    def _set_ctrl2(self, v):
        self._ctrl2 = PathPoint(v.x, v.y)
        self.__dirty = True
    
    ctrl1 = property(_get_ctrl1, _set_ctrl1)
    ctrl2 = property(_get_ctrl2, _set_ctrl2)
    
    def __eq__(self, pt):
        if not isinstance(pt, PathElement): return False
        return self.cmd == pt.cmd \
           and self.x == pt.x \
           and self.y == pt.y \
           and self.ctrl1 == pt.ctrl1 \
           and self.ctrl2 == pt.ctrl2
        
    def __ne__(self, pt):
        return not self.__eq__(pt)
        
    def __repr__(self):
        return "%s(cmd='%s', x=%.1f, y=%.1f, ctrl1=(%.1f, %.1f), ctrl2=(%.1f, %.1f))" % (
            self.__class__.__name__, self.cmd, self.x, self.y, 
            self.ctrl1.x, self.ctrl1.y, 
            self.ctrl2.x, self.ctrl2.y)

    def copy(self):
        if self.cmd == MOVETO \
        or self.cmd == LINETO:
            pts = ((self.x, self.y),)
        elif self.cmd == CURVETO:
            pts = ((self.ctrl1.x, self.ctrl1.y), (self.ctrl2.x, self.ctrl2.y), (self.x, self.y))
        else:
            pts = None
        return PathElement(self.cmd, pts)

class BezierPath(list):
    
    def __init__(self, path=None, **kwargs):
        """ A list of PathElements describing the curves and lines that make up the path.
        """
        if isinstance(path, (BezierPath, list, tuple)):
            self.extend([pt.copy() for pt in path])
        self._kwargs   = kwargs
        self._cache    = None # Cached vertices for drawing.
        self._segments = None # Cached segment lengths.
        self._bounds   = None # Cached bounding rectangle.
        self._polygon  = None # Cached polygon hit test area.
        self._dirty    = False
        self._index    = {}

    def copy(self):
        return BezierPath(self, **self._kwargs)
    
    def append(self, pt):
        self._dirty = True; list.append(self, pt)
    def extend(self, points):
        self._dirty = True; list.extend(self, points)
    def insert(self, i, pt):
        self._dirty = True; self._index={}; list.insert(self, i, pt)
    def remove(self, pt):
        self._dirty = True; self._index={}; list.remove(self, pt)
    def pop(self, i):
        self._dirty = True; self._index={}; list.pop(self, i)
    def __setitem__(self, i, pt):
        self._dirty = True; self._index={}; list.__setitem__(self, i, pt)
    def __delitem__(self, i):
        self._dirty = True; self._index={}; list.__delitem__(self, i)
    def sort(self):
        self._dirty = True; self._index={}; list.sort(self)
    def reverse(self):
        self._dirty = True; self._index={}; list.reverse(self)
    def index(self, pt):
        return self._index.setdefault(pt, list.index(self, pt))
    
    def _update(self):
        # Called from BezierPath.draw().
        # If points were added or removed, clear the cache.
        b = self._dirty
        for pt in self: b = b or pt._dirty; pt._dirty = False
        if b:
            if self._cache is not None:
                if self._cache[0]: flush(self._cache[0])
                if self._cache[1]: flush(self._cache[1])
            self._cache = self._segments = self._bounds = self._polygon = None
            self._dirty = False
    
    def moveto(self, x, y):
        """ Adds a new point to the path at x, y.
        """
        self.append(PathElement(MOVETO, ((x, y),)))
    
    def lineto(self, x, y):
        """ Adds a line from the previous point to x, y.
        """
        self.append(PathElement(LINETO, ((x, y),)))
        
    def curveto(self, x1, y1, x2, y2, x3, y3):
        """ Adds a Bezier-curve from the previous point to x3, y3.
            The curvature is determined by control handles x1, y1 and x2, y2.
        """
        self.append(PathElement(CURVETO, ((x1, y1), (x2, y2), (x3, y3))))
    
    def arcto(self, x, y, radius=1, clockwise=True, short=False):
        """ Adds a number of Bezier-curves that draw an arc with the given radius to (x,y).
            The short parameter selects either the "long way" around or the "shortcut".
        """
        x0, y0 = self[-1].x, self[-1].y
        phi = geometry.angle(x0,y0,x,y)
        for p in bezier.arcto(x0, y0, radius, radius, phi, short, not clockwise, x, y):
            f = len(p) == 2 and self.lineto or self.curveto
            f(*p)
    
    def closepath(self):
        """ Adds a line from the previous point to the last MOVETO.
        """
        self.append(PathElement(CLOSE))

    def rect(self, x, y, width, height, roundness=0.0):
        """ Adds a (rounded) rectangle to the path.
            Corner roundness can be given as a relative float or absolute int.
        """
        if roundness <= 0:
            self.moveto(x, y)
            self.lineto(x+width, y)
            self.lineto(x+width, y+height)
            self.lineto(x, y+height)
            self.lineto(x, y)
        else:
            if isinstance(roundness, int):
                r = min(roundness, width/2, height/2)
            else:
                r = min(width, height)
                r = min(roundness, 1) * r * 0.5
            self.moveto(x+r, y)
            self.lineto(x+width-r, y)
            self.arcto(x+width, y+r, radius=r, clockwise=False)
            self.lineto(x+width, y+height-r)
            self.arcto(x+width-r, y+height, radius=r, clockwise=False)
            self.lineto(x+r, y+height)
            self.arcto(x, y+height-r, radius=r, clockwise=False)
            self.lineto(x, y+r)
            self.arcto(x+r, y, radius=r, clockwise=False)
    
    def ellipse(self, x, y, width, height):
        """ Adds an ellipse to the path.
        """
        w, h = width*0.5, height*0.5
        k = 0.5522847498    # kappa: (-1 + sqrt(2)) / 3 * 4
        self.moveto(x, y-h) # http://www.whizkidtech.redprince.net/bezier/circle/
        self.curveto(x+w*k, y-h,   x+w,   y-h*k, x+w, y, )
        self.curveto(x+w,   y+h*k, x+w*k, y+h,   x,   y+h)
        self.curveto(x-w*k, y+h,   x-w,   y+h*k, x-w, y, )
        self.curveto(x-w,   y-h*k, x-w*k, y-h,   x,   y-h)
        self.closepath()
        
    oval = ellipse
    
    def arc(self, x, y, width, height, start=0, stop=90):
        """ Adds an arc to the path.
            The arc follows the ellipse defined by (x, y, width, height),
            with start and stop specifying what angle range to draw.
        """
        w, h = width*0.5, height*0.5
        for i, p in enumerate(bezier.arc(x-w, y-h, x+w, y+h, start, stop)):
            if i == 0:
                self.moveto(*p[:2])
            self.curveto(*p[2:])

    def smooth(self, *args, **kwargs):
        """ Smooths the path by making the curve handles colinear.
            With mode=EQUIDISTANT, the curve handles will be of equal (average) length.
        """
        e = BezierEditor(self)
        for i, pt in enumerate(self):
            self._index[pt] = i
            e.smooth(pt, *args, **kwargs)

    def flatten(self, precision=RELATIVE):
        """ Returns a list of contours, in which each contour is a list of (x,y)-tuples.
            The precision determines the number of straight lines to use as a substition for a curve.
            It can be a fixed number (int) or relative to the curve length (float or RELATIVE).
        """
        if precision == RELATIVE:
            precision = RELATIVE_PRECISION
        contours = [[]]
        x0, y0 = None, None
        closeto = None
        for pt in self:
            if (pt.cmd == LINETO or pt.cmd == CURVETO) and x0 == y0 is None:
                raise NoCurrentPointForPath
            elif pt.cmd == LINETO:
                contours[-1].append((x0, y0))
                contours[-1].append((pt.x, pt.y))
            elif pt.cmd == CURVETO:
                # Curves are interpolated from a number of straight line segments.
                # With relative precision, we use the (rough) curve length to determine the number of lines.
                x1, y1, x2, y2, x3, y3 =  pt.ctrl1.x, pt.ctrl1.y, pt.ctrl2.x, pt.ctrl2.y, pt.x, pt.y
                if isinstance(precision, float):
                    n = int(max(0, precision) * bezier.curvelength(x0, y0, x1, y1, x2, y2, x3, y3, 3))
                else:
                    n = int(max(0, precision))
                if n > 0:
                    xi, yi = x0, y0
                    for i in range(n+1):
                        xj, yj, vx1, vy1, vx2, vy2 = bezier.curvepoint(float(i)/n, x0, y0, x1, y1, x2, y2, x3, y3)
                        contours[-1].append((xi, yi))
                        contours[-1].append((xj, yj))
                        xi, yi = xj, yj
            elif pt.cmd == MOVETO:
                contours.append([]) # Start a new contour.
                closeto = pt
            elif pt.cmd == CLOSE and closeto is not None:
                contours[-1].append((x0, y0))
                contours[-1].append((closeto.x, closeto.y))
            x0, y0 = pt.x, pt.y
        return contours

    def draw(self, precision=RELATIVE, **kwargs):
        """ Draws the path.
            The precision determines the number of straight lines to use as a substition for a curve.
            It can be a fixed number (int) or relative to the curve length (float or RELATIVE).
        """
        if len(kwargs) > 0:
            # Optional parameters in draw() overrule those set during initialization. 
            kw = dict(self._kwargs)
            kw.update(kwargs)
            fill, stroke, strokewidth, strokestyle = color_mixin(**kw)
        else:
            fill, stroke, strokewidth, strokestyle = color_mixin(**self._kwargs)
        def _draw_fill(contours):
            # Drawing commands for the path fill (as triangles by tessellating the contours).
            v = geometry.tesselate(contours)
            glBegin(GL_TRIANGLES)
            for x, y in v:
                glVertex3f(x, y, 0)
            glEnd()
        def _draw_stroke(contours):
            # Drawing commands for the path stroke.
            for path in contours:
                glBegin(GL_LINE_STRIP)
                for x, y in path:
                    glVertex2f(x, y)
                glEnd()
        self._update() # Remove the cache if points were modified.
        if self._cache is None \
        or self._cache[0] is None and fill \
        or self._cache[1] is None and stroke \
        or self._cache[-1] != precision:
            # Calculate and cache the vertices as Display Lists.
            # If the path requires a fill color, it will have to be tessellated.
            if self._cache is not None:
                if self._cache[0]: flush(self._cache[0])
                if self._cache[1]: flush(self._cache[1])
            contours = self.flatten(precision)
            self._cache = [None, None, precision]
            if fill   : self._cache[0] = precompile(_draw_fill, contours)
            if stroke : self._cache[1] = precompile(_draw_stroke, contours)
        if fill is not None:
            glColor4f(fill[0], fill[1], fill[2], fill[3] * _alpha)
            glCallList(self._cache[0])
        if stroke is not None and strokewidth > 0:
            glColor4f(stroke[0], stroke[1], stroke[2], stroke[3] * _alpha)
            glLineWidth(strokewidth)
            glLineDash(strokestyle)
            glCallList(self._cache[1])

    def angle(self, t):
        """ Returns the directional angle at time t (0.0-1.0) on the path.
        """
        # The directed() enumerator is much faster but less precise.
        pt0, pt1 = t==0 and (self.point(t), self.point(t+0.001)) or (self.point(t-0.001), self.point(t))
        return geometry.angle(pt0.x, pt0.y, pt1.x, pt1.y)

    def point(self, t):
        """ Returns the PathElement at time t (0.0-1.0) on the path.
            See the linear interpolation math in bezier.py.
        """
        if self._segments is None:
            self._segments = bezier.length(self, segmented=True, n=10)
        return bezier.point(self, t, segments=self._segments)
    
    def points(self, amount=2, start=0.0, end=1.0):
        """ Returns a list of PathElements along the path.
            To omit the last point on closed paths: end=1-1.0/amount
        """
        if self._segments is None:
            self._segments = bezier.length(self, segmented=True, n=10)
        return bezier.points(self, amount, start, end, segments=self._segments)
    
    def addpoint(self, t):
        """ Inserts a new PathElement at time t (0.0-1.0) on the path.
        """
        self._segments = None
        self._index = {}
        return bezier.insert_point(self, t)
        
    split = addpoint
    
    @property 
    def length(self, precision=10):
        """ Returns an approximation of the total length of the path.
        """
        return bezier.length(self, segmented=False, n=precision)
    
    @property
    def contours(self):
        """ Returns a list of contours (i.e. segments separated by a MOVETO) in the path.
            Each contour is a BezierPath object.
        """
        return bezier.contours(self)

    @property
    def bounds(self, precision=100):
        """ Returns a (x, y, width, height)-tuple of the approximate path dimensions.
        """
        # In _update(), traverse all the points and check if they have changed.
        # If so, the bounds must be recalculated.
        self._update()
        if self._bounds is None:
            l = t = float( "inf")
            r = b = float("-inf")
            for pt in self.points(precision):
                if pt.x < l: l = pt.x
                if pt.y < t: t = pt.y
                if pt.x > r: r = pt.x
                if pt.y > b: b = pt.y
            self._bounds = (l, t, r-l, b-t)
        return self._bounds

    def contains(self, x, y, precision=100):
        """ Returns True when point (x,y) falls within the contours of the path.
        """
        bx, by, bw, bh = self.bounds
        if bx <= x <= bx+bw and \
           by <= y <= by+bh:
                if self._polygon is None \
                or self._polygon[1] != precision:
                    self._polygon = [(pt.x,pt.y) for pt in self.points(precision)], precision
                # Ray casting algorithm:
                return geometry.point_in_polygon(self._polygon[0], x, y)
        return False

    def hash(self, state=None, decimal=1):
        """ Returns the path id, based on the position and handles of its PathElements.
            Two distinct BezierPath objects that draw the same path therefore have the same id.
        """
        f = lambda x: int(x*10**decimal) # Format floats as strings with given decimal precision.
        id = [state]
        for pt in self: id.extend((
            pt.cmd, f(pt.x), f(pt.y), f(pt.ctrl1.x), f(pt.ctrl1.y), f(pt.ctrl2.x), f(pt.ctrl2.y)))
        id = str(id)
        id = md5(id).hexdigest()
        return id
    
    def __repr__(self):
        return "BezierPath(%s)" % repr(list(self))
    
    def __del__(self):
        # Note: it is important that __del__() is called since it unloads the cache from GPU.
        # BezierPath and PathElement should contain no circular references, e.g. no PathElement.parent.
        if hasattr(self, "_cache") and self._cache is not None and flush:
            if self._cache[0]: flush(self._cache[0])
            if self._cache[1]: flush(self._cache[1])

def drawpath(path, **kwargs):
    """ Draws the given BezierPath (or list of PathElements).
        The current stroke, strokewidth and fill color are applied.
    """
    if not isinstance(path, BezierPath):
        path = BezierPath(path)
    path.draw(**kwargs)

_autoclosepath = True
def autoclosepath(close=False):
    """ Paths constructed with beginpath() and endpath() are automatically closed.
    """
    global _autoclosepath
    _autoclosepath = close

_path = None
def beginpath(x, y):
    """ Starts a new path at (x,y).
        The commands moveto(), lineto(), curveto() and closepath() 
        can then be used between beginpath() and endpath() calls.
    """
    global _path
    _path = BezierPath()
    _path.moveto(x, y)

def moveto(x, y):
    """ Moves the current point in the current path to (x,y).
    """
    if _path is None: 
        raise NoCurrentPath
    _path.moveto(x, y)

def lineto(x, y):
    """ Draws a line from the current point in the current path to (x,y).
    """
    if _path is None: 
        raise NoCurrentPath
    _path.lineto(x, y)

def curveto(x1, y1, x2, y2, x3, y3):
    """ Draws a curve from the current point in the current path to (x3,y3).
        The curvature is determined by control handles x1, y1 and x2, y2.
    """
    if _path is None: 
        raise NoCurrentPath
    _path.curveto(x1, y1, x2, y2, x3, y3)

def closepath():
    """ Closes the current path with a straight line to the last MOVETO.
    """
    if _path is None: 
        raise NoCurrentPath
    _path.closepath()

def endpath(draw=True, **kwargs):
    """ Draws and returns the current path.
        With draw=False, only returns the path so it can be manipulated and drawn with drawpath().
    """
    global _path, _autoclosepath
    if _path is None: 
        raise NoCurrentPath
    if _autoclosepath is True:
        _path.closepath()
    if draw:
        _path.draw(**kwargs)
    p, _path = _path, None
    return p

def findpath(points, curvature=1.0):
    """ Returns a smooth BezierPath from the given list of (x,y)-tuples.
    """
    return bezier.findpath(list(points), curvature)

Path = BezierPath

#--- BEZIER EDITOR -----------------------------------------------------------------------------------

EQUIDISTANT = "equidistant"
IN, OUT, BOTH = "in", "out", "both" # Drag pt1.ctrl2, pt2.ctrl1 or both simultaneously?

class BezierEditor:
    
    def __init__(self, path):
        self.path = path
        
    def _nextpoint(self, pt):
        i = self.path.index(pt) # BezierPath caches this operation.
        return i < len(self.path)-1 and self.path[i+1] or None
    
    def translate(self, pt, x=0, y=0, h1=(0,0), h2=(0,0)):
        """ Translates the point and its control handles by (x,y).
            Translates the incoming handle by h1 and the outgoing handle by h2.
        """
        pt1, pt2 = pt, self._nextpoint(pt)
        pt1.x += x
        pt1.y += y
        pt1.ctrl2.x += x + h1[0]
        pt1.ctrl2.y += y + h1[1]
        if pt2 is not None:
            pt2.ctrl1.x += x + (pt2.cmd == CURVETO and h2[0] or 0)
            pt2.ctrl1.y += y + (pt2.cmd == CURVETO and h2[1] or 0)
            
    def rotate(self, pt, angle, handle=BOTH):
        """ Rotates the point control handles by the given angle.
        """
        pt1, pt2 = pt, self._nextpoint(pt)
        if handle == BOTH or handle == IN:
            pt1.ctrl2.x, pt1.ctrl2.y = geometry.rotate(pt1.ctrl2.x, pt1.ctrl2.y, pt1.x, pt1.y, angle)
        if handle == BOTH or handle == OUT and pt2 is not None and pt2.cmd == CURVETO:
            pt2.ctrl1.x, pt2.ctrl1.y = geometry.rotate(pt2.ctrl1.x, pt2.ctrl1.y, pt1.x, pt1.y, angle)
            
    def scale(self, pt, v, handle=BOTH):
        """ Scales the point control handles by the given factor.
        """
        pt1, pt2 = pt, self._nextpoint(pt)
        if handle == BOTH or handle == IN:
            pt1.ctrl2.x, pt1.ctrl2.y = bezier.linepoint(v, pt1.x, pt1.y, pt1.ctrl2.x, pt1.ctrl2.y)
        if handle == BOTH or handle == OUT and pt2 is not None and pt2.cmd == CURVETO:
            pt2.ctrl1.x, pt2.ctrl1.y = bezier.linepoint(v, pt1.x, pt1.y, pt2.ctrl1.x, pt2.ctrl1.y)

    def smooth(self, pt, mode=None, handle=BOTH):
        pt1, pt2, i = pt, self._nextpoint(pt), self.path.index(pt)
        if pt2 is None:
            return
        if pt1.cmd == pt2.cmd == CURVETO:
            if mode == EQUIDISTANT:
                d1 = d2 = 0.5 * (
                     geometry.distance(pt1.x, pt1.y, pt1.ctrl2.x, pt1.ctrl2.y) + \
                     geometry.distance(pt1.x, pt1.y, pt2.ctrl1.x, pt2.ctrl1.y))
            else:
                d1 = geometry.distance(pt1.x, pt1.y, pt1.ctrl2.x, pt1.ctrl2.y)
                d2 = geometry.distance(pt1.x, pt1.y, pt2.ctrl1.x, pt2.ctrl1.y)            
            if handle == IN: 
                a = geometry.angle(pt1.x, pt1.y, pt1.ctrl2.x, pt1.ctrl2.y)
            if handle == OUT: 
                a = geometry.angle(pt2.ctrl1.x, pt2.ctrl1.y, pt1.x, pt1.y)
            if handle == BOTH: 
                a = geometry.angle(pt2.ctrl1.x, pt2.ctrl1.y, pt1.ctrl2.x, pt1.ctrl2.y)
            pt1.ctrl2.x, pt1.ctrl2.y = geometry.coordinates(pt1.x, pt1.y, d1, a)
            pt2.ctrl1.x, pt2.ctrl1.y = geometry.coordinates(pt1.x, pt1.y, d2, a-180)
        elif pt1.cmd == CURVETO and pt2.cmd == LINETO:
            d = mode == EQUIDISTANT and \
                geometry.distance(pt1.x, pt1.y, pt2.x, pt2.y) or \
                geometry.distance(pt1.x, pt1.y, pt1.ctrl2.x, pt1.ctrl2.y)
            a = geometry.angle(pt1.x, pt1.y, pt2.x, pt2.y)
            pt1.ctrl2.x, pt1.ctrl2.y = geometry.coordinates(pt1.x, pt1.y, d, a-180)
        elif pt1.cmd == LINETO and pt2.cmd == CURVETO and i > 0:
            d = mode == EQUIDISTANT and \
                geometry.distance(pt1.x, pt1.y, self.path[i-1].x, self.path[i-1].y) or \
                geometry.distance(pt1.x, pt1.y, pt2.ctrl1.x, pt2.ctrl1.y)
            a = geometry.angle(self.path[i-1].x, self.path[i-1].y, pt1.x, pt1.y)
            pt2.ctrl1.x, pt2.ctrl1.y = geometry.coordinates(pt1.x, pt1.y, d, a)

#--- POINT ANGLES ------------------------------------------------------------------------------------

def directed(points):
    """ Returns an iterator that yields (angle, point)-tuples for the given list of points.
        The angle represents the direction of the point on the path.
        This works with BezierPath, Bezierpath.points, [pt1, pt2, pt2, ...]
        For example:
        for a, pt in directed(path.points(30)):
            push()
            translate(pt.x, pt.y)
            rotate(a)
            arrow(0, 0, 10)
            pop()
        This is useful if you want to have shapes following a path.
        To put text on a path, rotate the angle by +-90 to get the normal (i.e. perpendicular).
    """
    p = list(points)
    n = len(p)
    for i, pt in enumerate(p):
        if 0 < i < n-1 and pt.__dict__.get("_cmd") == CURVETO:
            # For a point on a curve, the control handle gives the best direction.
            # For PathElement (fixed point in BezierPath), ctrl2 tells us how the curve arrives.
            # For DynamicPathElement (returnd from BezierPath.point()), ctrl1 tell how the curve arrives.
            ctrl = isinstance(pt, bezier.DynamicPathElement) and pt.ctrl1 or pt.ctrl2
            angle = geometry.angle(ctrl.x, ctrl.y, pt.x, pt.y)
        elif 0 < i < n-1 and pt.__dict__.get("_cmd") == LINETO and p[i-1].__dict__.get("_cmd") == CURVETO:
            # For a point on a line preceded by a curve, look ahead gives better results.
            angle = geometry.angle(pt.x, pt.y, p[i+1].x, p[i+1].y)
        elif i == 0 and isinstance(points, BezierPath):
            # For the first point in a BezierPath, we can calculate a next point very close by.
            pt1 = points.point(0.001)
            angle = geometry.angle(pt.x, pt.y, pt1.x, pt1.y)
        elif i == n-1 and isinstance(points, BezierPath):
            # For the last point in a BezierPath, we can calculate a previous point very close by.
            pt0 = points.point(0.999)
            angle = geometry.angle(pt0.x, pt0.y, pt.x, pt.y)
        elif i == n-1 and isinstance(pt, bezier.DynamicPathElement) and pt.ctrl1.x != pt.x or pt.ctrl1.y != pt.y:
            # For the last point in BezierPath.points(), use incoming handle (ctrl1) for curves.
            angle = geometry.angle(pt.ctrl1.x, pt.ctrl1.y, pt.x, pt.y)
        elif 0 < i:
            # For any point, look back gives a good result, if enough points are given.
            angle = geometry.angle(p[i-1].x, p[i-1].y, pt.x, pt.y)
        elif i < n-1:
            # For the first point, the best (only) guess is the location of the next point.
            angle = geometry.angle(pt.x, pt.y, p[i+1].x, p[i+1].y)
        else:
            angle = 0
        yield angle, pt

#--- CLIPPING PATH -----------------------------------------------------------------------------------

class ClippingMask:
    def draw(self, fill=(0,0,0,1), stroke=None):
        pass

def beginclip(path):
    """ Enables the given BezierPath (or ClippingMask) as a clipping mask.
        Drawing commands between beginclip() and endclip() are constrained to the shape of the path.
    """
    # Enable the stencil buffer to limit the area of rendering (stenciling).
    glClear(GL_STENCIL_BUFFER_BIT)
    glEnable(GL_STENCIL_TEST)
    glStencilFunc(GL_NOTEQUAL, 0, 0)
    glStencilOp(GL_INCR, GL_INCR, GL_INCR)
    # Shouldn't depth testing be disabled when stencilling?
    # In any case, if it is, transparency doesn't work.
    #glDisable(GL_DEPTH_TEST)
    path.draw(fill=(0,0,0,1), stroke=None) # Disregard color settings; always use a black mask.
    #glEnable(GL_DEPTH_TEST)
    glStencilFunc(GL_EQUAL, 1, 1)
    glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)

def endclip():
    glDisable(GL_STENCIL_TEST)

#--- SUPERSHAPE --------------------------------------------------------------------------------------

def supershape(x, y, width, height, m, n1, n2, n3, points=100, percentage=1.0, range=2*pi, **kwargs):
    """ Returns a BezierPath constructed using the superformula,
        which can be used to describe many complex shapes and curves that are found in nature.
    """
    path = BezierPath()
    first = True
    for i in xrange(points):
        if i <= points * percentage: 
            dx, dy = geometry.superformula(m, n1, n2, n3, i*range/points)
            dx, dy = dx*width/2 + x, dy*height/2 + y
            if first is True:
                path.moveto(dx, dy); first=False
            else:
                path.lineto(dx, dy)
    path.closepath()
    if kwargs.get("draw", True):
        path.draw(**kwargs)
    return path

#=====================================================================================================

#--- IMAGE -------------------------------------------------------------------------------------------
# Textures and quad vertices are cached for performance.
# Textures remain in cache for the duration of the program.
# Quad vertices are cached as Display Lists and destroyed when the Image object is deleted.
# For optimal performance, images should be created once (not every frame) and its quads left unmodified.
# Performance should be comparable to (moving) pyglet.Sprites drawn in a batch.

pow2 = [2**n for n in range(20)] # [1, 2, 4, 8, 16, 32, 64, ...]

def ceil2(x):
    """ Returns the nearest power of 2 that is higher than x, e.g. 700 => 1024.
    """
    for y in pow2:
        if y >= x: return y

class ImageError(Exception): 
    pass

_texture_cache  = {} # pyglet.Texture referenced by filename.
_texture_cached = {} # pyglet.Texture.id is in keys once the image has been cached.
def texture(img, data=None):
    """ Returns a (cached) texture from the given image filename or byte data.
        When a Image or Pixels object is given, returns the associated texture.
    """
    # Image texture stored in cache, referenced by file path (or a custom id defined with cache()).
    if isinstance(img, (basestring, int)) and img in _texture_cache:
        return _texture_cache[img]
    # Image file path, load it, cache it, return texture.
    if isinstance(img, basestring):
        try: cache(img, pyglet.image.load(img).get_texture())
        except IOError:
            raise ImageError, "can't load image from %s" % repr(img)
        return _texture_cache[img]
    # Image texture, return original.
    if isinstance(img, pyglet.image.Texture):
        return img
    # Image object, return image texture.
    # (if you use this to create a new image, the new image will do expensive caching as well).
    if isinstance(img, Image):
        return img.texture
    # Pixels object, return pixel texture.
    if isinstance(img, Pixels):
        return img.texture
    # Pyglet image data.
    if isinstance(img, pyglet.image.ImageData):
        return img.texture
    # Image data as byte string, load it, return texture.
    if isinstance(data, basestring):
        return pyglet.image.load("", file=StringIO(data)).get_texture()
    # Don't know how to handle this image.
    raise ImageError, "unknown image type: %s" % repr(img.__class__)

def cache(id, texture):
    """ Store the given texture in cache, referenced by id (which can then be passed to image()).
        This is useful for procedurally rendered images (which are not stored in cache by default).
    """
    if isinstance(texture, (Image, Pixels)):
        texture = texture.texture
    if not isinstance(texture, pyglet.image.Texture):
        raise ValueError, "can only cache texture, not %s" % repr(texture.__class__.__name__)
    _texture_cache[id] = texture
    _texture_cached[_texture_cache[id].id] = id
    
def cached(texture):
    """ Returns the cache id if the texture has been cached (None otherwise).
    """
    if isinstance(texture, (Image, Pixels)):
        texture = texture.texture
    if isinstance(texture, pyglet.image.Texture):
        return _texture_cached.get(texture.texture.id)
    if isinstance(texture, (basestring, int)):
        return texture in _texture_cache and texture or None
    return None
    
def _render(texture, quad=(0,0,0,0,0,0,0,0)):
    """ Renders the texture on the canvas inside a quadtriliteral (i.e. rectangle).
        The quadriliteral can be distorted by giving corner offset coordinates.
    """
    t = texture.tex_coords # power-2 dimensions
    w = texture.width      # See Pyglet programming guide -> OpenGL imaging.
    h = texture.height
    dx1, dy1, dx2, dy2, dx3, dy3, dx4, dy4 = quad or (0,0,0,0,0,0,0,0)
    glEnable(texture.target)
    glBindTexture(texture.target, texture.id)
    glBegin(GL_QUADS)
    glTexCoord3f(t[0], t[1],  t[2] ); glVertex3f(dx4,   dy4,   0)
    glTexCoord3f(t[3], t[4],  t[5] ); glVertex3f(dx3+w, dy3,   0)
    glTexCoord3f(t[6], t[7],  t[8] ); glVertex3f(dx2+w, dy2+h, 0)
    glTexCoord3f(t[9], t[10], t[11]); glVertex3f(dx1,   dy1+h, 0)
    glEnd()
    glDisable(texture.target)

class Quad(list):
    
    def __init__(self, dx1=0, dy1=0, dx2=0, dy2=0, dx3=0, dy3=0, dx4=0, dy4=0):
        """ Describes the four-sided polygon on which an image texture is "mounted".
            This is a quadrilateral (four sides) of which the vertices do not necessarily
            have a straight angle (i.e. the corners can be distorted).
        """
        list.__init__(self, (dx1, dy1, dx2, dy2, dx3, dy3, dx4, dy4))
        self._dirty = True # Image objects poll Quad._dirty to check if the image cache is outdated.
    
    def copy(self):
        return Quad(*self)
    
    def reset(self):
        list.__init__(self, (0,0,0,0,0,0,0,0))
        self._dirty = True
    
    def __setitem__(self, i, v):
        list.__setitem__(self, i, v)
        self._dirty = True

    def _get_dx1(self): return self[0]
    def _get_dy1(self): return self[1]
    def _get_dx2(self): return self[2]
    def _get_dy2(self): return self[3]
    def _get_dx3(self): return self[4]
    def _get_dy3(self): return self[5]
    def _get_dx4(self): return self[6]
    def _get_dy4(self): return self[7]

    def _set_dx1(self, v): self[0] = v
    def _set_dy1(self, v): self[1] = v
    def _set_dx2(self, v): self[2] = v
    def _set_dy2(self, v): self[3] = v
    def _set_dx3(self, v): self[4] = v
    def _set_dy3(self, v): self[5] = v
    def _set_dx4(self, v): self[6] = v
    def _set_dy4(self, v): self[7] = v
    
    dx1 = property(_get_dx1, _set_dx1)
    dy1 = property(_get_dy1, _set_dy1)
    dx2 = property(_get_dx2, _set_dx2)
    dy2 = property(_get_dy2, _set_dy2)
    dx3 = property(_get_dx3, _set_dx3)
    dy3 = property(_get_dy3, _set_dy3)
    dx4 = property(_get_dx4, _set_dx4)
    dy4 = property(_get_dy4, _set_dy4)

class Image(object):
    
    def __init__(self, path, x=0, y=0, width=None, height=None, alpha=1.0, data=None):
        """ A texture that can be drawn at a given position.
            The quadrilateral in which the texture is drawn can be distorted (slow, image cache is flushed).
            The image can be resized, colorized and its opacity can be set.
        """
        self._src     = (path, data)
        self._texture = texture(path, data=data)
        self._cache   = None
        self.x        = x
        self.y        = y
        self.width    = width  or self._texture.width  # Scaled width, Image.texture.width yields original width.
        self.height   = height or self._texture.height # Scaled height, Image.texture.height yields original height.
        self.quad     = Quad()
        self.color    = Color(1.0, 1.0, 1.0, alpha)
    
    def copy(self, texture=None, width=None, height=None):
        img = texture is None \
          and self.__class__(self._src[0], data=self._src[1]) \
           or self.__class__(texture)
        img.x      = self.x
        img.y      = self.y
        img.width  = self.width
        img.height = self.height
        img.quad   = self.quad.copy()
        img.color  = self.color.copy()
        if width is not None: 
            img.width = width
        if height is not None: 
            img.height = height
        return img
    
    @property
    def id(self):
        return self._texture.id
    
    @property
    def texture(self):
        return self._texture

    def _get_xy(self):
        return (self.x, self.y)
    def _set_xy(self, (x,y)):
        self.x = x
        self.y = y
        
    xy = property(_get_xy, _set_xy)

    def _get_size(self):
        return (self.width, self.height)
    def _set_size(self, (w,h)):
        self.width  = w
        self.height = h
        
    size = property(_get_size, _set_size)
    
    def _get_alpha(self):
        return self.color[3]
    def _set_alpha(self, v):
        self.color[3] = v
        
    alpha = property(_get_alpha, _set_alpha)

    def distort(self, dx1=0, dy1=0, dx2=0, dy2=0, dx3=0, dy3=0, dx4=0, dy4=0):
        """ Adjusts the four-sided polygon on which an image texture is "mounted",
            by incrementing the corner coordinates with the given values.
        """
        for i, v in enumerate((dx1, dy1, dx2, dy2, dx3, dy3, dx4, dy4)):
            if v != 0: 
                self.quad[i] += v

    def adjust(r=1.0, g=1.0, b=1.0, a=1.0):
        """ Adjusts the image color by multiplying R,G,B,A channels with the given values.
        """
        self.color[0] *= r
        self.color[1] *= g
        self.color[2] *= b
        self.color[3] *= a
        
    def draw(self, x=None, y=None, width=None, height=None, alpha=None, color=None, filter=None):
        """ Draws the image.
            The given parameters (if any) override the image's attributes.
        """
        # Calculate and cache the quad vertices as a Display List.
        # If the quad has changed, update the cache.
        if self._cache is None or self.quad._dirty:
            flush(self._cache)
            self._cache = precompile(_render, self._texture, self.quad)
            self.quad._dirty = False
        # Given parameters override Image attributes.
        if x is None: 
            x = self.x
        if y is None: 
            y = self.y
        if width is None: 
            width = self.width 
        if height is None: 
            height = self.height
        if color and len(color) < 4:
            color = color[0], color[1], color[2], 1.0
        if color is None: 
            color = self.color
        if alpha is not None:
            color = color[0], color[1], color[2], alpha
        if filter:
            filter.texture = self._texture # Register the current texture with the filter.
            filter.push()
        # Round position (x,y) to nearest integer to avoid sub-pixel rendering.
        # This ensures there are no visual artefacts on transparent borders (e.g. the "white halo").
        # Halo can also be avoided by overpainting in the source image, but this requires some work:
        # http://technology.blurst.com/remove-white-borders-in-transparent-textures/
        x = round(x)
        y = round(y)
        w = float(width) / self._texture.width
        h = float(height) / self._texture.height
        # Transform and draw the quads.
        glPushMatrix()
        glTranslatef(x, y, 0)
        glScalef(w, h, 0)
        glColor4f(color[0], color[1], color[2], color[3] * _alpha)
        glCallList(self._cache)
        glPopMatrix() 
        if filter:
            filter.pop()
    
    def save(self, path):
        """ Exports the image as a PNG-file.
        """
        self._texture.save(path)
    
    def __repr__(self):
        return "%s(x=%.1f, y=%.1f, width=%.1f, height=%.1f, alpha=%.2f)" % (
            self.__class__.__name__, self.x, self.y, self.width, self.height, self.alpha)
    
    def __del__(self):
        if hasattr(self, "_cache") and self._cache is not None and flush:
            flush(self._cache)

_IMAGE_CACHE = 200
_image_cache = {} # Image object referenced by Image.texture.id.
_image_queue = [] # Most recent id's are at the front of the list.
def image(img, x=None, y=None, width=None, height=None, 
          alpha=None, color=None, filter=None, data=None, draw=True):
    """ Draws the image at (x,y), scaling it to the given width and height.
        The image's transparency can be set with alpha (0.0-1.0).
        Applies the given color adjustment, quad distortion and filter (one filter can be specified).
        Note: with a filter enabled, alpha and color will not be applied.
        This is because the filter overrides the default drawing behavior with its own.
    """
    if not isinstance(img, Image):
        # If the given image is not an Image object, create one on the fly.
        # This object is cached for reuse.
        # The cache has a limited size (200), so the oldest Image objects are deleted.
        t = texture(img, data=data)
        if t.id in _image_cache: 
            img = _image_cache[t.id]
        else:
            img = Image(img, data=data)
            _image_cache[img.texture.id] = img
            _image_queue.insert(0, img.texture.id)
            for id in reversed(_image_queue[_IMAGE_CACHE:]): 
                del _image_cache[id]
                del _image_queue[-1]
    # Draw the image.
    if draw:
        img.draw(x, y, width, height, alpha, color, filter)
    return img

def imagesize(img):
    """ Returns a (width, height)-tuple with the image dimensions.
    """
    t = texture(img)
    return (t.width, t.height)

def crop(img, x=0, y=0, width=None, height=None):
    """ Returns the given (x, y, width, height)-region from the image.
        Use this to pass cropped image files to image().
    """
    t = texture(img)
    if width  is None: width  = t.width
    if height is None: height = t.height
    t = t.get_region(x, y, min(t.width-x, width), min(t.height-y, height))
    if isinstance(img, Image):
        img = img.copy(texture=t)
        return img.copy(texture=t, width=t.width, height=t.height)
    if isinstance(img, Pixels):
        return Pixels(t)
    if isinstance(img, pyglet.image.Texture):
        return t
    return Image(t)

#--- PIXELS ------------------------------------------------------------------------------------------

class Pixels(list):
    
    def __init__(self, img):
        """ A list of RGBA color values (0-255) for each pixel in the given image.
            The Pixels object can be passed to the image() command.
        """
        self._img  = texture(img).get_image_data()
        # A negative pitch means the pixels are stored top-to-bottom row.
        self._flipped = self._img.pitch >= 0
        # Data yields a byte array if no conversion (e.g. BGRA => RGBA) was necessary,
        # or a byte string otherwise - which needs to be converted to a list of ints.
        data = self._img.get_data("RGBA", self._img.width*4 * (-1,1)[self._flipped])
        if isinstance(data, str):
            data = map(ord, list(data))
        # Some formats seem to store values from -1 to -256.
        data = [(256+v)%256 for v in data]
        self.array = data
        self._texture  = None
    
    @property
    def width(self):
        return self._img.width

    @property
    def height(self):
        return self._img.height

    @property
    def size(self):
        return (self.width, self.height)

    def __len__(self):
        return len(self.array) / 4
    
    def __iter__(self):
        for i in xrange(len(self)):
            yield self[i]
    
    def __getitem__(self, i):
        """ Returns a list of R,G,B,A channel values between 0-255 from pixel i.
            Users need to wrap the list in a Color themselves for performance.
            - r,g,b,a = Pixels[i]
            - clr = color(Pixels[i], base=255)
        """
        return self.array[i*4:i*4+4]
    
    def __setitem__(self, i, v):
        """ Sets pixel i to the given R,G,B,A values.
            Users need to unpack a Color themselves for performance,
            and are resposible for keeping channes values between 0 and 255
            (otherwise an error will occur when Pixels.update() is called),
            - Pixels[i] = r,g,b,a
            - Pixels[i] = clr.map(base=255)
        """
        for j in range(4):
            self.array[i*4+j] = v[j]
    
    def __getslice__(self, i, j):
        return [self[i+n] for n in xrange(j-i)]
    
    def __setslice__(self, i, j, seq):
        for n in xrange(j-i):
            self[i+n] = seq[n]
            
    def map(self, function):
        """ Applies a function to each pixel.
            Function takes a list of R,G,B,A channel values and must return a similar list.
        """
        for i in xrange(len(self)):
            self[i] = function(self[i])
            
    def get(self, i, j):
        """ Returns the pixel at row i, column j as a Color object.
        """
        if 0 <= i < self.width and 0 <= j < self.height:
            return color(self[i+j*self.width], base=255)
    
    def set(self, i, j, clr):
        """ Sets the pixel at row i, column j from a Color object.
        """
        if 0 <= i < self.width and 0 <= j < self.height:
            self[i+j*self.width] = clr.map(base=255)
    
    def update(self):
        """ Pixels.update() must be called to refresh the image.
        """
        data = self.array
        data = "".join(map(chr, data))
        self._img.set_data("RGBA", self._img.width*4*(-1,1)[self._flipped], data)
        self._texture = self._img.get_texture()
        
    @property
    def texture(self):
        if self._texture is None:
            self.update()
        return self._texture
        
    def copy(self):
        return Pixels(self.texture)
        
    def __repr__(self):
        return "%s(width=%.1f, height=%.1f)" % (
            self.__class__.__name__, self.width, self.height)

pixels = Pixels

#--- ANIMATION ---------------------------------------------------------------------------------------
# A sequence of images displayed in a loop.
# Useful for storing pre-rendered effect frames like explosions etc.

class Animation(list):
    
    def __init__(self, images=[], duration=None, loop=False, **kwargs):
        """ Constructs an animation loop from the given image frames.
            The duration specifies the time for the entire animation to run.
            Animations are useful to cache effects like explosions,
            that have for example been prepared in an offscreen buffer.
        """
        list.__init__(self, list(images))
        self.duration = duration # Duration of the entire animation.
        self.loop     = loop     # Loop from last frame to first frame?
        self._i       = -1       # Frame counter.
        self._t = Transition(0, interpolation=kwargs.get("interpolation", LINEAR))
    
    def copy(self, **kwargs):
        return Animation(self, 
              duration = kwargs.get("duration", self.duration), 
                  loop = kwargs.get("loop", self.loop), 
         interpolation = self._t._interpolation)
    
    def update(self):
        if self.duration is not None:
            # With a duration,
            # skip to a next frame so that the entire animation takes the given time.
            if self._i < 0 or self.loop and self._i == len(self)-1:
                self._t.set(0, 0)
                self._t.update()
                self._t.set(len(self)-1, self.duration)
            self._t.update()
            self._i = int(self._t.current)
        else:
            # Without a duration,
            # Animation.update() simply moves to the next frame.
            if self._i < 0 or self.loop and self._i == len(self)-1:
                self._i = -1
            self._i = min(self._i+1, len(self)-1)
    
    @property
    def frames(self):
        return self
        
    @property
    def frame(self):
        # Yields the current frame Image (or None).
        try: return self[self._i]
        except:
            return None
        
    @property
    def done(self):
        # Yields True when the animation has stopped (or hasn't started).
        return self.loop is False and self._i == len(self)-1
    
    def draw(self, *args, **kwargs):
        if not self.done:
            image(self.frame, *args, **kwargs)
            
    def __repr__(self):
        return "%s(frames=%i, duration=%s)" % (
            self.__class__.__name__, len(self), repr(self.duration))

animation = Animation

#--- OFFSCREEN RENDERING -----------------------------------------------------------------------------
# Offscreen buffers can be used to render images from paths etc. 
# or to apply filters on images before drawing them to the screen.
# There are several ways to draw offscreen:
# - render(img, filter): applies the given filter to the image and returns it.
# - procedural(function, width, height): execute the drawing commands in function inside an image.
# - Create your own subclass of OffscreenBuffer with a draw() method:
#   class MyBuffer(OffscreenBuffer):
#       def draw(self): pass
# - Define drawing commands between OffscreenBuffer.push() and pop():
#   b = MyBuffer()
#   b.push()
#   # drawing commands
#   b.pop()
#   img = Image(b.render())
#
# The shader.py module already defines several filters that use an offscreen buffer, for example:
# blur(), adjust(), multiply(), twirl(), ...
#
# The less you change about an offscreen buffer, the faster it runs.
# This includes switching it on and off and changing its size.

from shader import *

#=====================================================================================================

#--- FONT --------------------------------------------------------------------------------------------

def install_font(ttf):
    """ Loads the given TrueType font from file, and returns True on success.
    """
    try: 
        pyglet.font.add_file(ttf)
        return True
    except:
        # This might fail with Carbon on 64-bit Mac systems.
        # Fonts can be installed on the system manually if this is the case.
        return False

# Load the platform-independent fonts shipped with NodeBox.
# The default font is Droid (licensed under Apache 2.0).
try:
    for f in glob(path.join(path.dirname(__file__), "..", "font", "*")):
        install_font(f)
    DEFAULT_FONT = "Droid Sans"
except:
    DEFAULT_FONT = "Arial"

# Font weight
NORMAL = "normal"
BOLD   = "bold"
ITALIC = "italic"

# Text alignment
LEFT   = "left"
RIGHT  = "right"
CENTER = "center"

_fonts      = []             # Custom fonts loaded from file.
_fontname   = DEFAULT_FONT   # Current state font name.
_fontsize   = 12             # Current state font size.
_fontweight = [False, False] # Current state font weight (bold, italic).
_lineheight = 1.0            # Current state text lineheight.
_align      = LEFT           # Current state text alignment (LEFT/RIGHT/CENTER).

def font(fontname=None, fontsize=None, fontweight=None, file=None):
    """ Sets the current font and/or fontsize.
        If a filename is also given, loads the fontname from the given font file.
    """
    global _fontname, _fontsize
    if file is not None and file not in _fonts:
        _fonts.append(file); install_font(file)
    if fontname is not None:
        _fontname = fontname
    if fontsize is not None:
        _fontsize = fontsize
    if fontweight is not None:
        _fontweight_(fontweight) # _fontweight_() is just an alias for fontweight().
    return _fontname

def fontname(name=None):
    """ Sets the current font used when drawing text.
    """
    global _fontname
    if name is not None:
        _fontname = name
    return _fontname

def fontsize(size=None):
    """ Sets the current fontsize in points.
    """
    global _fontsize
    if size is not None:
        _fontsize = size
    return _fontsize
    
def fontweight(*args, **kwargs):
    """ Sets the current font weight.
        You can supply NORMAL, BOLD and/or ITALIC or set named parameters bold=True and/or italic=True.
    """
    global _fontweight
    if len(args) == 1 and isinstance(args, (list, tuple)):
        args = args[0]
    if NORMAL in args:
        _fontweight = [False, False]
    if BOLD in args or kwargs.get(BOLD):
        _fontweight[0] = True
    if ITALIC in args or kwargs.get(ITALIC):
        _fontweight[1] = True
    return _fontweight
    
_fontweight_ = fontweight

def lineheight(size=None):
    """ Sets the vertical spacing between lines of text.
        The given size is a relative value: lineheight 1.2 for fontsize 10 means 12.
    """
    global _lineheight
    if size is not None:
        _lineheight = size
    return _lineheight

def align(mode=None):
    """ Sets the alignment of text paragrapgs (LEFT, RIGHT or CENTER).
    """
    global _align
    if mode is not None:
        _align = mode
    return _align

#--- FONT MIXIN --------------------------------------------------------------------------------------
# The text() command has optional parameters font, fontsize, fontweight, bold, italic, lineheight and align.

def font_mixin(**kwargs):
    fontname   = kwargs.get("fontname", kwargs.get("font", _fontname))
    fontsize   = kwargs.get("fontsize", _fontsize)
    bold       = kwargs.get("bold", BOLD in kwargs.get("fontweight", "") or _fontweight[0])
    italic     = kwargs.get("italic", ITALIC in kwargs.get("fontweight", "") or _fontweight[1])
    lineheight = kwargs.get("lineheight", _lineheight)
    align      = kwargs.get("align", _align)
    return (fontname, fontsize, bold, italic, lineheight, align) 

#--- TEXT --------------------------------------------------------------------------------------------
# Text is cached for performance.
# For optimal performance, texts should be created once (not every frame) and left unmodified.
# Dynamic texts use a cache of recycled Text objects.

# pyglet.text.Label leaks memory when deleted, because its old batch continues to reference
# loaded font/fontsize/bold/italic glyphs.
# Adding all labels to our own batch remedies this.
_label_batch = pyglet.graphics.Batch()

def label(str="", width=None, height=None, **kwargs):
    """ Returns a drawable pyglet.text.Label object from the given string.
        Optional arguments include: font, fontsize, bold, italic, align, lineheight, fill.
        If these are omitted the current state is used.
    """
    fontname, fontsize, bold, italic, lineheight, align = font_mixin(**kwargs)
    fill, stroke, strokewidth, strokestyle = color_mixin(**kwargs)
    fill = fill is None and (0,0,0,0) or fill
    # We use begin_update() so that the TextLayout doesn't refresh on each update.
    # FormattedDocument allows individual styling of characters - see Text.style().
    label = pyglet.text.Label(batch=_label_batch)
    label.begin_update()
    label.document = pyglet.text.document.FormattedDocument(str)
    label.width     = width    
    label.height    = height
    label.font_name = fontname
    label.font_size = fontsize
    label.bold      = bold
    label.italic    = italic
    label.multiline = True
    label.anchor_y  = "bottom"
    label.set_style("align", align)
    label.set_style("line_spacing", lineheight * fontsize)
    label.color     = [int(ch*255) for ch in fill]
    label.end_update()
    return label

class Text(object):
    
    def __init__(self, str, x=0, y=0, width=None, height=None, **kwargs):
        """ A formatted string of text that can be drawn at a given position.
            Text has the following properties: 
            text, x, y, width, height, font, fontsize, bold, italic, lineheight, align, fill.
            Individual character ranges can be styled with Text.style().
        """
        if width is None:
            # Supplying a string with "\n" characters will crash if no width is given.
            # On the outside it appears as None but inside we use a very large number.
            width = geometry.INFINITE
            a, kwargs["align"] = kwargs.get("align", _align), LEFT
        else:
            a = None
        self.__dict__["x"]      = x
        self.__dict__["y"]      = y
        self.__dict__["_label"] = label(str, width, height, **kwargs)
        self.__dict__["_dirty"] = False
        self.__dict__["_align"] = a
        self.__dict__["_fill"]  = None

    def _get_xy(self):
        return (self.x, self.y)
    def _set_xy(self, (x,y)):
        self.x = x
        self.y = y
        
    xy = property(_get_xy, _set_xy)
    
    def _get_size(self):
        return (self.width, self.height)
    def _set_size(self, (w,h)):
        self.width  = w
        self.height = h
        
    size = property(_get_size, _set_size)
    
    def __getattr__(self, k):
        if k in self.__dict__:
            return self.__dict__[k]
        elif k in ("text", "height", "bold", "italic"):
            return getattr(self._label, k)
        elif k == "string":
            return self._label.text
        elif k == "width":
            if self._label.width != geometry.INFINITE: return self._label.width
        elif k in ("font", "fontname"):
            return self._label.font_name
        elif k == "fontsize":
            return self._label.font_size
        elif k == "fontweight":
            return ((None, BOLD)[self._label.bold], (None, ITALIC)[self._label.italic])
        elif k == "lineheight":
            return self._label.get_style("line_spacing") / (self.fontsize or 1)
        elif k == "align":
            if not self._align: self._align = self._label.get_style(k)
            return self._align
        elif k == "fill":
            if not self._fill: self._fill = Color([ch/255.0 for ch in self._label.color])
            return self._fill
        else:
            raise AttributeError, "'Text' object has no attribute '%s'" % k
            
    def __setattr__(self, k, v):
        if k in self.__dict__:
            self.__dict__[k] = v; return
        # Setting properties other than x and y requires the label's layout to be updated.
        self.__dict__["_dirty"] = True
        self._label.begin_update()
        if k in ("text", "height", "bold", "italic"):
            setattr(self._label, k, v)
        elif k == "string":
            self._label.text = v
        elif k == "width":
            self._label.width = v is None and geometry.INFINITE or v
        elif k in ("font", "fontname"):
            self._label.font_name = v
        elif k == "fontsize":
            self._label.font_size = v
        elif k == "fontweight":
            self._label.bold, self._label.italic = BOLD in v, ITALIC in v
        elif k == "lineheight":
            self._label.set_style("line_spacing", v * (self.fontsize or 1))
        elif k == "align":
            self._align = v
            self._label.set_style(k, self._label.width == geometry.INFINITE and LEFT or v)
        elif k == "fill":
            self._fill = v 
            self._label.color = [int(255*ch) for ch in self._fill or (0,0,0,0)]
        else:
            raise AttributeError, "'Text' object has no attribute '%s'" % k
    
    def _update(self):
        # Called from Text.draw(), Text.copy() and Text.metrics.
        # Ensures that all the color changes have been reflected in Text._label.
        # If necessary, recalculates the label's layout (happens in end_update()).
        if hasattr(self._fill, "_dirty") and self._fill._dirty:
            self.fill = self._fill
            self._fill._dirty = False
        if self._dirty:
            self._label.end_update()
            self._dirty = False
    
    @property
    def path(self):
        raise NotImplementedError
    
    @property
    def metrics(self):
        """ Yields a (width, height)-tuple of the actual text content.
        """
        self._update()
        return self._label.content_width, self._label.content_height
        
    def draw(self, x=None, y=None):
        """ Draws the text.
        """
        # Given parameters override Text attributes.
        if x is None:
            x = self.x
        if y is None:
            y = self.y
        # Fontsize is rounded, and fontsize 0 will output a default font.
        # Therefore, we don't draw text with a fontsize smaller than 0.5.
        if self._label.font_size >= 0.5:
            glPushMatrix()
            glTranslatef(x, y, 0)
            self._update()
            self._label.draw()
            glPopMatrix()
    
    def copy(self):
        self._update()
        txt = Text(self.text, self.x, self.y, self.width, self.height, 
              fontname = self.fontname,
              fontsize = self.fontsize,
                  bold = self.bold,
                italic = self.italic,
            lineheight = self.lineheight,
                 align = self.align,
                  fill = self.fill
        )
        # The individual character styling is retrieved from Label.document._style_runs.
        # Traverse it and set the styles in the new text.
        txt._label.begin_update()
        for k in self._label.document._style_runs:
            for i, j, v in self._label.document._style_runs[k]:
                txt.style(i,j, **{k:v})
        txt._label.end_update()
        return txt
        
    def style(self, i, j, **kwargs):
        """ Defines the styling for a range of characters in the text.
            Valid arguments can include: font, fontsize, bold, italic, lineheight, align, fill.
            For example: text.style(0, 10, bold=True, fill=color(1,0,0))
        """
        attributes = {}
        for k,v in kwargs.items():
            if k in ("font", "fontname"):
                attributes["font_name"] = v
            elif k == "fontsize":
                attributes["font_size"] = v
            elif k in ("bold", "italic", "align"):
                attributes[k] = v
            elif k == "fontweight":
                attributes.setdefault("bold", BOLD in v)
                attributes.setdefault("italic", ITALIC in v)
            elif k == "lineheight":
                attributes["line_spacing"] = v * self._label.font_size
            elif k == "fill":
                attributes["color"] = [int(ch*255) for ch in v]
            else:
                attributes[k] = v
        self._dirty = True
        self._label.begin_update()
        self._label.document.set_style(i, j, attributes)

    def __len__(self):
        return len(self.text)

    def __del__(self):
        if hasattr(self, "_label") and self._label:
            self._label.delete()

_TEXT_CACHE = 200
_text_cache = {}
_text_queue = []
def text(str, x=None, y=None, width=None, height=None, draw=True, **kwargs):
    """ Draws the string at the given position, with the current font().
        Lines of text will span the given width before breaking to the next line.
        The text will be displayed with the current state font(), fontsize(), fontweight(), etc.
        When the given text is a Text object, the state will not be applied.
    """
    if isinstance(str, Text) and width is None and height is None and len(kwargs) == 0:
        txt = str
    else:
        # If the given text is not a Text object, create one on the fly.
        # Dynamic Text objects are cached by (font, fontsize, bold, italic),
        # and those that are no longer referenced by the user are recycled.
        # Changing Text properties is still faster than creating a new Text.
        # The cache has a limited size (200), so the oldest Text objects are deleted.
        fontname, fontsize, bold, italic, lineheight, align = font_mixin(**kwargs)
        fill, stroke, strokewidth, strokestyle = color_mixin(**kwargs)
        id = (fontname, int(fontsize), bold, italic)
        recycled = False
        if id in _text_cache:
            for txt in _text_cache[id]:
                # Reference count 3 => Python, _text_cache[id], txt.
                # No other variables are referencing the text, so we can recycle it.
                if getrefcount(txt) == 3:
                    txt.text = str
                    txt.x = x or 0
                    txt.y = y or 0
                    txt.width = width
                    txt.height = height
                    txt.lineheight = lineheight
                    txt.align = align
                    txt.fill = fill
                    recycled = True
                    break
        if not recycled:
            txt = Text(str, x or 0, y or 0, width, height, **kwargs)
            _text_cache.setdefault(id, [])
            _text_cache[id].append(txt)
            _text_queue.insert(0, id)
            for id in reversed(_text_queue[_TEXT_CACHE:]): 
                del _text_cache[id][0]
                del _text_queue[-1]
    if draw:
        txt.draw(x, y)
    return txt

def textwidth(txt, **kwargs):
    """ Returns the width of the given text.
    """
    if not isinstance(txt, Text) or len(kwargs) > 0:
        kwargs["draw"] = False
        txt = text(txt, 0, 0, **kwargs)
    return txt.metrics[0]

def textheight(txt, width=None, **kwargs):
    """ Returns the height of the given text.
    """
    if not isinstance(txt, Text) or len(kwargs) > 0 or width != txt.width:
        kwargs["draw"] = False
        txt = text(txt, 0, 0, width=width, **kwargs)
    return txt.metrics[1]

def textmetrics(txt, width=None, **kwargs):
    """ Returns a (width, height)-tuple for the given text.
    """
    if not isinstance(txt, Text) or len(kwargs) > 0 or width != txt.width:
        kwargs["draw"] = False
        txt = text(txt, 0, 0, width=width, **kwargs)
    return txt.metrics

#--- TEXTPATH ----------------------------------------------------------------------------------------

class GlyphPathError(Exception):
    pass

import cPickle
glyphs = {}
try:
    # Load cached font glyph path information from nodebox/font/glyph.p.
    # By default, it has glyph path info for Droid Sans, Droid Sans Mono, Droid Serif.
    glyphs = path.join(path.dirname(__file__), "..", "font", "glyph.p")
    glyphs = cPickle.load(open(glyphs))
except:
    pass

def textpath(string, x=0, y=0, **kwargs):
    """ Returns a BezierPath from the given text string.
        The fontname, fontsize and fontweight can be given as optional parameters,
        width, height, lineheight and align are ignored.
        Only works with ASCII characters in the default fonts (Droid Sans, Droid Sans Mono, Droid Serif, Arial).
        See nodebox/font/glyph.py on how to activate other fonts.
    """
    fontname, fontsize, bold, italic, lineheight, align = font_mixin(**kwargs)
    w = bold and italic and "bold italic" or bold and "bold" or italic and "italic" or "normal"
    p = BezierPath()
    f = fontsize / 1000.0
    for ch in string:
        try: glyph = glyphs[fontname][w][ch]
        except:
            raise GlyphPathError, "no glyph path information for %s %s '%s'" % (w, fontname, ch)
        for pt in glyph:
            if pt[0] == MOVETO:
                p.moveto(x+pt[1]*f, y-pt[2]*f)
            elif pt[0] == LINETO:
                p.lineto(x+pt[1]*f, y-pt[2]*f)
            elif pt[0] == CURVETO:
                p.curveto(x+pt[3]*f, y-pt[4]*f, x+pt[5]*f, y-pt[6]*f, x+pt[1]*f, y-pt[2]*f)
            elif pt[0] == CLOSE:
                p.closepath()
        x += textwidth(ch, font=fontname, fontsize=fontsize, bold=bold, italic=italic)
    return p

#=====================================================================================================

#--- UTILITIES ---------------------------------------------------------------------------------------

_RANDOM_MAP = [90.0, 9.00, 4.00, 2.33, 1.50, 1.00, 0.66, 0.43, 0.25, 0.11, 0.01]
def _rnd_exp(bias=0.5): 
    bias = max(0, min(bias, 1)) * 10
    i = int(floor(bias))             # bias*10 => index in the _map curve.
    n = _RANDOM_MAP[i]               # If bias is 0.3, rnd()**2.33 will average 0.3.
    if bias < 10:
        n += (_RANDOM_MAP[i+1]-n) * (bias-i)
    return n

def random(v1=1.0, v2=None, bias=None):
    """ Returns a number between v1 and v2, including v1 but not v2.
        The bias (0.0-1.0) represents preference towards lower or higher numbers.
    """
    if v2 is None:
        v1, v2 = 0, v1
    if bias is None:
        r = rnd()
    else:
        r = rnd()**_rnd_exp(bias)
    x = r * (v2-v1) + v1
    if isinstance(v1, int) and isinstance(v2, int):
        x = int(x)
    return x

def grid(cols, rows, colwidth=1, rowheight=1, shuffled=False):
    """ Yields (x,y)-tuples for the given number of rows and columns.
        The space between each point is determined by colwidth and colheight.
    """
    rows = range(int(rows))
    cols = range(int(cols))
    if shuffled:
        shuffle(rows)
        shuffle(cols)
    for y in rows:
        for x in cols:
            yield (x*colwidth, y*rowheight)

def files(path="*"):
    """ Returns a list of files found at the given path.
    """
    return glob(path)

#=====================================================================================================

#--- PROTOTYPE ----------------------------------------------------------------------------------------

class Prototype(object):
    
    def __init__(self):
        """ A base class that allows on-the-fly extension.
            This means that external functions can be bound to it as methods,
            and properties set at runtime are copied correctly.
            Prototype can handle: 
            - functions (these become class methods),
            - immutable types (str, unicode, int, long, float, bool),
            - lists, tuples and dictionaries of immutable types, 
            - objects with a copy() method.
        """
        self._dynamic = {}

    def _deepcopy(self, value):
        if isinstance(value, FunctionType):
            return instancemethod(value, self)
        elif hasattr(value, "copy"):
            return value.copy()
        elif isinstance(value, (list, tuple)):
            return [self._deepcopy(x) for x in value]
        elif isinstance(value, dict):
            return dict([(k, self._deepcopy(v)) for k,v in value.items()])
        elif isinstance(value, (str, unicode, int, long, float, bool)):
            return value
        else:
            # Biggest problem here is how to find/relink circular references.
            raise TypeError, "Prototype can't bind %s." % str(value.__class__)

    def _bind(self, key, value):
        """ Adds a new method or property to the prototype.
            For methods, the given function is expected to take the object (i.e. self) as first parameter.
            For properties, values can be: list, tuple, dict, str, unicode, int, long, float, bool,
            or an object with a copy() method.
            For example, we can define a Layer's custom draw() method in two ways:
            - By subclassing:
                class MyLayer(Layer):
                    def draw(layer):
                        pass
                layer = MyLayer()
                layer.draw()
            - By function binding:
                def my_draw(layer):
                    pass
                layer = Layer()
                layer._bind("draw", my_draw)
                layer.draw()
        """
        self._dynamic[key] = value
        object.__setattr__(self, key, self._deepcopy(value))
        
    def set_method(self, function, name=None):
        """ Creates a dynamic method (with the given name) from the given function.
        """
        if not name: 
            name = function.__name__
        self._bind(name, function)
    
    def set_property(self, key, value):
        """ Adds a property to the prototype.
            Using this method ensures that dynamic properties are copied correctly - see inherit().
        """
        self._bind(key, value)
    
    def inherit(self, prototype):
        """ Inherit all the dynamic properties and methods of another prototype.
        """
        for k,v in prototype._dynamic.items():
            self._bind(k,v)

#=====================================================================================================

#--- EVENT HANDLER ------------------------------------------------------------------------------------

class EventHandler:
    
    def __init__(self):
        # Use __dict__ directly so we can do multiple inheritance in combination with Prototype:
        self.__dict__["enabled"] = True  # Receive events from the canvas?
        self.__dict__["focus"]   = False # True when this object receives the focus.
        self.__dict__["pressed"] = False # True when the mouse is pressed on this object.
        self.__dict__["dragged"] = False # True when the mouse is dragged on this object.
        self.__dict__["_queue"]  = []
        
    def on_mouse_enter(self, mouse):
        pass
    def on_mouse_leave(self, mouse):
        pass
    def on_mouse_motion(self, mouse):
        pass
    def on_mouse_press(self, mouse):
        pass
    def on_mouse_release(self, mouse):
        pass
    def on_mouse_drag(self, mouse):
        pass
    def on_mouse_scroll(self, mouse):
        pass
    
    def on_key_press(self, keys):
        pass
    def on_key_release(self, keys):
        pass
    
    # Instead of calling an event directly it could be queued,
    # e.g. layer.queue_event(layer.on_mouse_press, canvas.mouse).
    # layer.process_events() can then be called whenever desired,
    # e.g. after the canvas has been drawn so that events can contain drawing commands.
    def queue_event(self, event, *args):
        self._queue.append((event, args))
    def process_events(self):
        for event, args in self._queue:
            event(*args)
        self._queue = []
    
    # Note: there is no event propagation.
    # Event propagation means that, for example, if a layer is pressed
    # all its child (or parent) layers receive an on_mouse_press() event as well.
    # If this kind of behavior is desired, it is the responsibility of custom subclasses of Layer.

#=====================================================================================================

#--- TRANSITION --------------------------------------------------------------------------------------
# Transition.update() will tween from the last value to transition.set() new value in the given time.
# Transitions are used as attributes (e.g. position, rotation) for the Layer class.

TIME = 0 # the current time in this frame changes when the canvas is updated
    
LINEAR = "linear"
SMOOTH = "smooth"

class Transition(object):

    def __init__(self, value, interpolation=SMOOTH):
        self._v0 = value # Previous value => Transition.start.
        self._vi = value # Current value  => Transition.current.
        self._v1 = value # Desired value  => Transition.stop.
        self._t0 = TIME  # Start time.
        self._t1 = TIME  # End time.
        self._interpolation = interpolation
    
    def copy(self):
        t = Transition(None)
        t._v0 = self._v0
        t._vi = self._vi
        t._v1 = self._v1
        t._t0 = self._t0
        t._t1 = self._t1
        t._interpolation = self._interpolation
        return t
    
    def get(self):
        """ Returns the transition stop value.
        """
        return self._v1
        
    def set(self, value, duration=1.0):
        """ Sets the transition stop value, which will be reached in the given duration (seconds).
            Calling Transition.update() moves the Transition.current value toward Transition.stop.
        """
        if duration == 0:
            # If no duration is given, Transition.start = Transition.current = Transition.stop.
            self._vi = value
        self._v1 = value
        self._v0 = self._vi
        self._t0 = TIME # Now.
        self._t1 = TIME + duration

    @property
    def start(self):
        return self._v0
    @property
    def stop(self):
        return self._v1
    @property 
    def current(self): 
        return self._vi
    
    @property
    def done(self):
        return TIME >= self._t1
    
    def update(self):
        """ Calculates the new current value. Returns True when done.
            The transition approaches the desired value according to the interpolation:
            - LINEAR: even transition over the given duration time,
            - SMOOTH: transition goes slower at the beginning and end.
        """
        if TIME >= self._t1 or self._vi is None:
            self._vi = self._v1
            return True
        else:
            # Calculate t: the elapsed time as a number between 0.0 and 1.0.
            t = (TIME-self._t0) / (self._t1-self._t0)
            if self._interpolation == LINEAR:
                self._vi = self._v0 + (self._v1-self._v0) * t
            else:
                self._vi = self._v0 + (self._v1-self._v0) * geometry.smoothstep(0.0, 1.0, t)
            return False

#--- LAYER -------------------------------------------------------------------------------------------
# The Layer class is responsible for the following:
# - it has a draw() method to override; all sorts of NodeBox drawing commands can be put here,
# - it has a transformation origin point and rotates/scales its drawn items as a group,
# - it has child layers that transform relative to this layer,
# - when its attributes (position, scale, angle, ...) change, they will tween smoothly over time. 

_UID = 0
def _uid():
    global _UID; _UID+=1; return _UID

RELATIVE = "relative" # Origin point is stored as float, e.g. (0.5, 0.5).
ABSOLUTE = "absolute" # Origin point is stored as int, e.g. (100, 100).

class LayerRenderError(Exception):
    pass

# When Layer.clipped=True, children are clipped to the bounds of the layer.
# The layer clipping masks lazily changes size with the layer.
class LayerClippingMask(ClippingMask):
    def __init__(self, layer):
        self.layer = layer
    def draw(self, fill=(0,0,0,1), stroke=None):
        w = not self.layer.width  and geometry.INFINITE or self.layer.width
        h = not self.layer.height and geometry.INFINITE or self.layer.height
        rect(0, 0, w, h, fill=fill, stroke=stroke)

class Layer(list, Prototype, EventHandler):

    def __init__(self, x=0, y=0, width=None, height=None, origin=(0,0), 
                 scale=1.0, rotation=0, opacity=1.0, duration=0.0, name=None, 
                 parent=None, **kwargs):
        """ Creates a new drawing layer that can be appended to the canvas.
            The duration defines the time (seconds) it takes to animate transformations or opacity.
            When the animation has terminated, layer.done=True.
        """
        if origin == CENTER:
            origin = (0.5,0.5)
            origin_mode = RELATIVE
        elif isinstance(origin[0], float) \
         and isinstance(origin[1], float):
            origin_mode = RELATIVE
        else:
            origin_mode = ABSOLUTE
        Prototype.__init__(self) # Facilitates extension on the fly.
        EventHandler.__init__(self)
        self._id       = _uid()
        self.name      = name                  # Layer name. Layers are accessible as ParentLayer.[name]
        self.canvas    = None                  # The canvas this layer is drawn to.
        self.parent    = parent                # The layer this layer is a child of.
        self._x        = Transition(x)         # Layer horizontal position in pixels, from the left.
        self._y        = Transition(y)         # Layer vertical position in pixels, from the bottom.
        self._width    = Transition(width)     # Layer width in pixels.
        self._height   = Transition(height)    # Layer height in pixels.
        self._dx       = Transition(origin[0]) # Transformation origin point.
        self._dy       = Transition(origin[1]) # Transformation origin point.
        self._origin   = origin_mode           # Origin point as RELATIVE or ABSOLUTE coordinates?
        self._scale    = Transition(scale)     # Layer width and height scale.
        self._rotation = Transition(rotation)  # Layer rotation.
        self._opacity  = Transition(opacity)   # Layer opacity.
        self.duration  = duration              # The time it takes to animate transformations.
        self.top       = True                  # Draw on top of or beneath parent?
        self.flipped   = False                 # Flip the layer horizontally?
        self.clipped   = False                 # Clip child layers to bounds?
        self.hidden    = False                 # Hide the layer?
        self._transform_cache = None           # Cache of the local transformation matrix.
        self._transform_stack = None           # Cache of the cumulative transformation matrix.
        self._clipping_mask   = LayerClippingMask(self)
    
    @classmethod
    def from_image(self, img, *args, **kwargs):
        """ Returns a new layer that renders the given image, and with the same size as the image.
            The layer's draw() method and an additional image property are set.
        """
        if not isinstance(img, Image):
            img = Image(img, data=kwargs.get("data"))
        kwargs.setdefault("width", img.width)
        kwargs.setdefault("height", img.height)
        def draw(layer):
            image(layer.image)
        layer = self(*args, **kwargs)
        layer.set_method(draw)
        layer.set_property("image", img)
        return layer
        
    @classmethod
    def from_function(self, function, *args, **kwargs):
        """ Returns a new layer that renders the drawing commands in the given function.
            The layer's draw() method is set.
        """
        def draw(layer):
            function(layer)
        layer = self(*args, **kwargs)
        layer.set_method(draw)
        return layer
        
    def copy(self, parent=None, canvas=None):
        """ Returns a copy of the layer.
            All Layer properties will be copied, except for the new parent and canvas,
            which you need to define as optional parameters.
            This means that copies are not automatically appended to the parent layer or canvas.
        """
        layer           = self.__class__() # Create instance of the derived class, not Layer.
        layer.duration  = 0                # Copy all transitions instantly.
        layer.canvas    = canvas
        layer.parent    = parent
        layer.name      = self.name
        layer._x        = self._x.copy()
        layer._y        = self._y.copy()
        layer._width    = self._width.copy()
        layer._height   = self._height.copy()
        layer._origin   = self._origin
        layer._dx       = self._dx.copy()
        layer._dy       = self._dy.copy()
        layer._scale    = self._scale.copy()
        layer._rotation = self._rotation.copy()
        layer._opacity  = self._opacity.copy()
        layer.duration  = self.duration
        layer.top       = self.top
        layer.flipped   = self.flipped
        layer.clipped   = self.clipped
        layer.hidden    = self.hidden
        layer.enabled   = self.enabled
        # Use base Layer.extend(), we don't care about what subclass.extend() does.
        Layer.extend(layer, [child.copy() for child in self])
        # Inherit all the dynamic properties and methods.
        Prototype.inherit(layer, self)
        return layer

    def __getattr__(self, key):
        """ Returns the given property, or the layer with the given name.
        """
        if key in self.__dict__: 
            return self.__dict__[key]
        for layer in self:
            if layer.name == key: 
                return layer
        raise AttributeError, "%s instance has no attribute '%s'" % (self.__class__.__name__, key)
    
    def _set_container(self, key, value):
        # If Layer.canvas is set to None, the canvas should no longer contain the layer.
        # If Layer.canvas is set to Canvas, this canvas should contain the layer.
        # Remove the layer from the old canvas/parent.
        # Append the layer to the new container.
        if self in (self.__dict__.get(key) or ()):
            self.__dict__[key].remove(self)
        if isinstance(value, list) and self not in value:
            list.append(value, self)
        self.__dict__[key] = value
        
    def _get_canvas(self):
        return self.__dict__.get("canvas")
    def _get_parent(self):
        return self.__dict__.get("parent")

    def _set_canvas(self, canvas):
        self._set_container("canvas", canvas)        
    def _set_parent(self, layer):
        self._set_container("parent", layer)

    canvas = property(_get_canvas, _set_canvas)    
    parent = property(_get_parent, _set_parent)

    @property
    def root(self):
        return self.parent and self.parent.root or self

    @property
    def layers(self):
        return self

    def insert(self, index, layer):
        list.insert(self, index, layer)
        layer.__dict__["parent"] = self
    def append(self, layer):
        list.append(self, layer)
        layer.__dict__["parent"] = self
    def extend(self, layers):
        for layer in layers:
            Layer.append(self, layer)
    def remove(self, layer):
        list.remove(self, layer)
        layer.__dict__["parent"] = None
    def pop(self, index):
        layer = list.pop(self, index)
        layer.__dict__["parent"] = None
        return layer
        
    def _get_x(self):
        return self._x.get()
    def _get_y(self):
        return self._y.get()
    def _get_width(self):
        return self._width.get()
    def _get_height(self):
        return self._height.get()
    def _get_scale(self):
        return self._scale.get()
    def _get_rotation(self):
        return self._rotation.get()
    def _get_opacity(self):
        return self._opacity.get()

    def _set_x(self, x):
        self._transform_cache = None
        self._x.set(x, self.duration)
    def _set_y(self, y):
        self._transform_cache = None
        self._y.set(y, self.duration)
    def _set_width(self, width):
        self._transform_cache = None
        self._width.set(width, self.duration)
    def _set_height(self, height):
        self._transform_cache = None
        self._height.set(height, self.duration)
    def _set_scale(self, scale):
        self._transform_cache = None
        self._scale.set(scale, self.duration)
    def _set_rotation(self, rotation):
        self._transform_cache = None
        self._rotation.set(rotation, self.duration)
    def _set_opacity(self, opacity):
        self._opacity.set(opacity, self.duration)

    x        = property(_get_x, _set_x)
    y        = property(_get_y, _set_y)
    width    = property(_get_width, _set_width)
    height   = property(_get_height, _set_height)
    scaling  = property(_get_scale, _set_scale)
    rotation = property(_get_rotation, _set_rotation)
    opacity  = property(_get_opacity, _set_opacity)

    def _get_xy(self):
        return (self.x, self.y)
    def _set_xy(self, (x,y)):
        self.x = x
        self.y = y
        
    xy = property(_get_xy, _set_xy)
    
    def _get_origin(self, relative=False):
        """ Returns the point (x,y) from which all layer transformations originate.
            When relative=True, x and y are defined percentually (0.0-1.0) in terms of width and height.
            In some cases x=0 or y=0 is returned:
            - For an infinite layer (width=None or height=None), we can't deduct the absolute origin
              from coordinates stored relatively (e.g. what is infinity*0.5?).
            - Vice versa, for an infinite layer we can't deduct the relative origin from coordinates
              stored absolute (e.g. what is 200/infinity?).
        """
        dx = self._dx.current
        dy = self._dy.current
        w  = self._width.current
        h  = self._height.current
        # Origin is stored as absolute coordinates and we want it relative.
        if self._origin == ABSOLUTE and relative:
            if w is None: w = 0
            if h is None: h = 0
            dx = w!=0 and dx/w or 0
            dy = h!=0 and dy/h or 0
        # Origin is stored as relative coordinates and we want it absolute.
        elif self._origin == RELATIVE and not relative:
            dx = w is not None and dx*w or 0
            dy = h is not None and dy*h or 0
        return dx, dy
    
    def _set_origin(self, x, y, relative=False):
        """ Sets the transformation origin point in either absolute or relative coordinates.
            For example, if a layer is 400x200 pixels, setting the origin point to (200,100)
            all transformations (translate, rotate, scale) originate from the center.
        """
        self._transform_cache = None
        self._dx.set(x, self.duration)
        self._dy.set(y, self.duration)
        self._origin = relative and RELATIVE or ABSOLUTE
    
    def origin(self, x=None, y=None, relative=False):
        """ Sets or returns the point (x,y) from which all layer transformations originate.
        """
        if x is not None:
            if x == CENTER: 
                x, y, relative = 0.5, 0.5, True
            if y is not None: 
                self._set_origin(x, y, relative)
        return self._get_origin(relative)
    
    def _get_relative_origin(self):
        return self.origin(relative=True)
    def _set_relative_origin(self, xy):
        self._set_origin(xy[0], xy[1], relative=True)
        
    relative_origin = property(_get_relative_origin, _set_relative_origin)
    
    def _get_absolute_origin(self):
        return self.origin(relative=False)
    def _set_absolute_origin(self, xy):
        self._set_origin(xy[0], xy[1], relative=False)
        
    absolute_origin = property(_get_absolute_origin, _set_absolute_origin)

    def _get_visible(self):
        return not self.hidden
    def _set_visible(self, b):
        self.hidden = not b
        
    visible = property(_get_visible, _set_visible)
    
    def translate(self, x, y):
        self.x += x
        self.y += y
        
    def rotate(self, angle):
        self.rotation += angle
        
    def scale(self, f):
        self.scaling *= f
        
    def flip(self):
        self.flipped = not self.flipped
    
    def _update(self):
        """ Called each frame from canvas._update() to update the layer transitions.
        """
        done  = self._x.update()
        done &= self._y.update()
        done &= self._width.update()
        done &= self._height.update()
        done &= self._dx.update()
        done &= self._dy.update()
        done &= self._scale.update()
        done &= self._rotation.update()
        if not done: # i.e. the layer is being transformed
            self._transform_cache = None
        self._opacity.update()
        self.update()
        for layer in self:
            layer._update()
            
    def update(self):
        """Override this method to provide custom updating code.
        """
        pass
    
    @property
    def done(self):
        """ Returns True when all transitions have finished.
        """
        return self._x.done \
           and self._y.done \
           and self._width.done \
           and self._height.done \
           and self._dx.done \
           and self._dy.done \
           and self._scale.done \
           and self._rotation.done \
           and self._opacity.done

    def _draw(self):
        """ Draws the transformed layer and all of its children.
        """
        if self.hidden:
            return
        glPushMatrix()
        # Be careful that the transformations happen in the same order in Layer._transform().
        # translate => flip => rotate => scale => origin.
        # Center the contents around the origin point.
        dx, dy = self.origin(relative=False)
        glTranslatef(round(self._x.current), round(self._y.current), 0)
        if self.flipped:
            glScalef(-1, 1, 1)
        glRotatef(self._rotation.current, 0, 0, 1)
        glScalef(self._scale.current, self._scale.current, 1)
        # Enable clipping mask if Layer.clipped=True.
        if self.clipped:
            beginclip(self._clipping_mask)
        # Draw child layers below.
        for layer in self:
            if layer.top is False:
                layer._draw()
        # Draw layer.
        global _alpha
        _alpha = self._opacity.current # XXX should also affect child layers?
        glPushMatrix()
        glTranslatef(-round(dx), -round(dy), 0) # Layers are drawn relative from parent origin.
        self.draw()
        glPopMatrix()
        _alpha = 1
        # Draw child layers on top.
        for layer in self:
            if layer.top is True:
                layer._draw()
        if self.clipped:
            endclip()
        glPopMatrix()
        
    def draw(self):
        """Override this method to provide custom drawing code for this layer.
            At this point, the layer is correctly transformed.
        """
        pass
        
    def render(self):
        """ Returns the layer as a flattened image.
            The layer and all of its children need to have width and height set.
        """
        b = self.bounds
        if geometry.INFINITE in (b.x, b.y, b.width, b.height):
            raise LayerRenderError, "can't render layer of infinite size"
        return render(lambda: (translate(-b.x,-b.y), self._draw()), b.width, b.height)
            
    def layer_at(self, x, y, clipped=False, enabled=False, transformed=True, _covered=False):
        """ Returns the topmost layer containing the mouse position, None otherwise.
            With clipped=True, no parts of child layers outside the parent's bounds are checked.
            With enabled=True, only enabled layers are checked (useful for events).
        """
        if self.hidden:
            # Don't do costly operations on layers the user can't see.
            return None
        if enabled and not self.enabled:
            # Skip disabled layers during event propagation.
            return None
        if _covered:
            # An ancestor is blocking this layer, so we can't select it.
            return None
        hit = self.contains(x, y, transformed)
        if clipped:
            # If (x,y) is not inside the clipped bounds, return None.
            # If children protruding beyond the layer's bounds are clipped,
            # we only need to look at children on top of the layer.
            # Each child is drawn on top of the previous child,
            # so we hit test them in reverse order (highest-first).
            if not hit: 
                return None
            children = [layer for layer in reversed(self) if layer.top is True]
        else:
            # Otherwise, traverse all children in on-top-first order to avoid
            # selecting a child underneath the layer that is in reality
            # covered by a peer on top of the layer, further down the list.
            children = sorted(reversed(self), key=lambda layer: not layer.top)
        for child in children:
            # An ancestor (e.g. grandparent) may be covering the child.
            # This happens when it hit tested and is somewhere on top of the child.
            # We keep a recursive covered-state to verify visibility.
            # The covered-state starts as False, but stays True once it switches.
            _covered = _covered or (hit and not child.top)
            child = child.layer_at(x, y, clipped, enabled, transformed, _covered)
            if child is not None:
                # Note: "if child:" won't work because it can be an empty list (no children). 
                # Should be improved by not having Layer inherit from list.
                return child
        if hit:
            return self
        else:
            return None
        
    def _transform(self, local=True):
        """ Returns the transformation matrix of the layer:
            a calculated state of its translation, rotation and scaling.
            If local=False, prepends all transformations of the parent layers,
            i.e. you get the absolute transformation state of a nested layer.
        """
        if self._transform_cache is None:
            # Calculate the local transformation matrix.
            # Be careful that the transformations happen in the same order in Layer._draw().
            # translate => flip => rotate => scale => origin.
            tf = Transform()
            dx, dy = self.origin(relative=False)
            tf.translate(round(self._x.current), round(self._y.current))
            if self.flipped:
                tf.scale(-1, 1)
            tf.rotate(self._rotation.current)
            tf.scale(self._scale.current, self._scale.current)
            tf.translate(-round(dx), -round(dy))
            self._transform_cache = tf
            # Flush the cumulative transformation cache of all children.
            def _flush(layer):
                layer._transform_stack = None
            self.traverse(_flush)
        if not local:
            # Return the cumulative transformation matrix.
            # All of the parent transformation states need to be up to date.
            # If not, we need to recalculate the whole chain.
            if self._transform_stack is None:
                if self.parent is None:
                    self._transform_stack = self._transform_cache.copy()
                else:
                    # Accumulate all the parent layer transformations.
                    # In the process, we update the transformation state of any outdated parent.
                    dx, dy = self.parent.origin(relative=False)
                    # Layers are drawn relative from parent origin.
                    tf = self.parent._transform(local=False).copy()
                    tf.translate(round(dx), round(dy))
                    self._transform_stack = self._transform_cache.copy()
                    self._transform_stack.prepend(tf)          
            return self._transform_stack
        return self._transform_cache

    @property
    def transform(self):
        return self._transform(local=False)

    def _bounds(self, local=True):
        """ Returns the rectangle that encompasses the transformed layer and its children.
            If one of the children has width=None or height=None, bounds will be infinite.
        """
        w = self._width.current; w = w is None and geometry.INFINITE or w
        h = self._height.current; h = h is None and geometry.INFINITE or h
        # Find the transformed bounds of the layer:
        p = self.transform.map([(0,0), (w,0), (w,h), (0,h)])
        x = min(p[0][0], p[1][0], p[2][0], p[3][0])
        y = min(p[0][1], p[1][1], p[2][1], p[3][1])
        w = max(p[0][0], p[1][0], p[2][0], p[3][0]) - x
        h = max(p[0][1], p[1][1], p[2][1], p[3][1]) - y
        b = geometry.Bounds(x, y, w, h)
        if not local:
            for child in self: 
                b = b.union(child.bounds)
        return b

    @property
    def bounds(self):
        return self._bounds(local=False)

    def contains(self, x, y, transformed=True):
        """ Returns True if (x,y) falls within the layer's rectangular area.
            Useful for GUI elements: with transformed=False the calculations are much faster;
            and it will report correctly as long as the layer (or parent layer)
            is not rotated or scaled, and has its origin at (0,0).
        """
        w = self._width.current; w = w is None and geometry.INFINITE or w
        h = self._height.current; h = h is None and geometry.INFINITE or h
        if not transformed:
            x0, y0 = self.absolute_position()
            return x0 <= x <= x0+w \
               and y0 <= y <= y0+h
        # Find the transformed bounds of the layer:
        p = self.transform.map([(0,0), (w,0), (w,h), (0,h)])
        return geometry.point_in_polygon(p, x, y)
        
    hit_test = contains

    def absolute_position(self, root=None):
        """ Returns the absolute (x,y) position (i.e. cumulative with parent position).
        """
        x = 0
        y = 0
        layer = self
        while layer is not None and layer != root:
            x += layer.x
            y += layer.y
            layer = layer.parent
        return x, y
    
    def traverse(self, visit=lambda layer: None):
        """ Recurses the layer structure and calls visit() on each child layer.
        """
        visit(self)
        [layer.traverse(visit) for layer in self]
        
    def __repr__(self):
        return "Layer(%sx=%.2f, y=%.2f, scale=%.2f, rotation=%.2f, opacity=%.2f, duration=%.2f)" % (
            self.name is not None and "name='%s', " % self.name or "", 
            self.x, 
            self.y, 
            self.scaling, 
            self.rotation, 
            self.opacity, 
            self.duration
        )
        
    def __eq__(self, other):
        return isinstance(other, Layer) and self._id == other._id
    def __ne__(self, other):
        return not self.__eq__(other)

layer = Layer

#--- GROUP -------------------------------------------------------------------------------------------

class Group(Layer):
    
    def __init__(self, *args, **kwargs):
        """ A layer that serves as a container for other layers.
            It has no width or height and doesn't draw anything.
        """
        Layer.__init__(self, *args, **kwargs)
        self._set_width(0)
        self._set_height(0)
        
    @classmethod
    def from_image(*args, **kwargs):
        raise NotImplementedError

    @classmethod
    def from_function(*args, **kwargs):
        raise NotImplementedError

    @property
    def width(self):
        return 0
    @property
    def height(self):
        return 0
        
    def layer_at(self, x, y, clipped=False, enabled=False, transformed=True, _covered=False):
        # Ignores clipped=True for Group (since it has no width or height).
        for child in reversed(self):
            layer = child.layer_at(x, y, clipped, enabled, transformed, _covered)
            if layer:
                return layer

group = Group

#=====================================================================================================

#--- MOUSE -------------------------------------------------------------------------------------------

# Mouse cursors:
DEFAULT = "default"
HIDDEN  = "hidden"
CROSS   = pyglet.window.Window.CURSOR_CROSSHAIR
HAND    = pyglet.window.Window.CURSOR_HAND
TEXT    = pyglet.window.Window.CURSOR_TEXT
WAIT    = pyglet.window.Window.CURSOR_WAIT

# Mouse buttons:
LEFT    = "left"
RIGHT   = "right"
MIDDLE  = "middle"

class Mouse(Point):
    
    def __init__(self, canvas, x=0, y=0):
        """ Keeps track of the mouse position on the canvas, buttons pressed and the cursor icon.
        """
        Point.__init__(self, x, y)
        self._canvas   = canvas
        self._cursor   = DEFAULT    # Mouse cursor: CROSS, HAND, HIDDEN, TEXT, WAIT.
        self._button   = None       # Mouse button pressed: LEFT, RIGHT, MIDDLE.
        self.modifiers = []         # Mouse button modifiers: CTRL, SHIFT, OPTION.
        self.pressed   = False      # True if the mouse button is pressed.
        self.dragged   = False      # True if the mouse is dragged.
        self.scroll    = Point(0,0) # Scroll offset.
        self.dx        = 0          # Relative offset from previous horizontal position.
        self.dy        = 0          # Relative offset from previous vertical position.

    # Backwards compatibility due to an old typo:
    @property
    def vx(self):
        return self.dx
    @property
    def vy(self):
        return self.dy

    @property
    def relative_x(self):
        try: return float(self.x) / self._canvas.width
        except ZeroDivisionError:
            return 0
    @property
    def relative_y(self):
        try: return float(self.y) / self._canvas.height
        except ZeroDivisionError:
            return 0

    def _get_cursor(self):
        return self._cursor
    def _set_cursor(self, mode):
        self._cursor = mode != DEFAULT and mode or None
        if mode == HIDDEN:
            self._canvas._window.set_mouse_visible(False); return
        self._canvas._window.set_mouse_cursor(
            self._canvas._window.get_system_mouse_cursor(
                self._cursor))
        
    cursor = property(_get_cursor, _set_cursor)
    
    def _get_button(self):
        return self._button
    def _set_button(self, button):
        self._button = \
            button == pyglet.window.mouse.LEFT   and LEFT or \
            button == pyglet.window.mouse.RIGHT  and RIGHT or \
            button == pyglet.window.mouse.MIDDLE and MIDDLE or None
            
    button = property(_get_button, _set_button)

    def __repr__(self):
        return "Mouse(x=%.1f, y=%.1f, pressed=%s, dragged=%s)" % (
            self.x, self.y, repr(self.pressed), repr(self.dragged))

#--- KEYBOARD ----------------------------------------------------------------------------------------

# Key codes:
BACKSPACE = "backspace"
DELETE    = "delete"
TAB       = "tab"
ENTER     = "enter"
SPACE     = "space"
ESCAPE    = "escape"
UP        = "up"
DOWN      = "down"
LEFT      = "left"
RIGHT     = "right"

# Key modifiers:
OPTION  = \
ALT     = "option"
CTRL    = "ctrl"
SHIFT   = "shift"
COMMAND = "command"

MODIFIERS = (OPTION, CTRL, SHIFT, COMMAND)

class Keys(list):
    
    def __init__(self, canvas):
        """ Keeps track of the keys pressed and any modifiers (e.g. shift or control key).
        """
        self._canvas   = canvas
        self.code      = None   # Last key pressed
        self.char      = ""     # Last key character representation (i.e., SHIFT + "a" = "A").
        self.modifiers = []     # Modifier keys pressed (OPTION, CTRL, SHIFT, COMMAND).
        self.pressed   = False


    def append(self, code):
        code = self._decode(code)
        if code in MODIFIERS:
            self.modifiers.append(code)
        list.append(self, code)
        self.code = self[-1]
    
    def remove(self, code):
        code = self._decode(code)
        if code in MODIFIERS:
            self.modifiers.remove(code)
        list.remove(self, self._decode(code))
        self.code = len(self) > 0 and self[-1] or None

    def _decode(self, code):
        if not isinstance(code, int):
            s = code
        else:
            s = pyglet.window.key.symbol_string(code)         # 65288 => "BACKSPACE"
            s = s.lower()                                     # "BACKSPACE" => "backspace"
            s = s.lstrip("_")                                 # "_1" => "1"
            s = s.replace("return", ENTER)                    # "return" => "enter"
            s = s.replace("num_", "")                         # "num_space" => "space"
            s = s.endswith(MODIFIERS) and s.lstrip("lr") or s # "lshift" => "shift"
        return s
                
    def __repr__(self):
        return "Keys(char=%s, code=%s, modifiers=%s, pressed=%s)" % (
            repr(self.char), repr(iter(self)), repr(self.modifiers), repr(self.pressed))

#=====================================================================================================

#--- CANVAS ------------------------------------------------------------------------------------------

VERY_LIGHT_GREY = 0.95

FRAME = 0

# Window styles.
WINDOW_DEFAULT    = pyglet.window.Window.WINDOW_STYLE_DEFAULT
WINDOW_BORDERLESS = pyglet.window.Window.WINDOW_STYLE_BORDERLESS

# Configuration settings for the canvas.
# http://www.pyglet.org/doc/programming_guide/opengl_configuration_options.html
# The stencil buffer is enabled (we need it to do clipping masks).
# Multisampling will be enabled (if possible) to do anti-aliasing.
settings = OPTIMAL = dict(
#      buffer_size = 32, # Let Pyglet decide automatically.
#         red_size = 8,
#       green_size = 8,
#        blue_size = 8,
        depth_size = 24,
      stencil_size = 1,
        alpha_size = 8, 
     double_buffer = 1,
    sample_buffers = 1, 
           samples = 4
)

def _configure(settings):
    """ Returns a pyglet.gl.Config object from the given dictionary of settings.
        If the settings are not supported, returns the default settings.
    """
    screen = pyglet.window.get_platform().get_default_display().get_default_screen()
    c = pyglet.gl.Config(**settings)
    try:
        c = screen.get_best_config(c)
    except pyglet.window.NoSuchConfigException:
        # Probably the hardwarde doesn't support multisampling.
        # We can still do some anti-aliasing by turning on GL_LINE_SMOOTH.
        c = pyglet.gl.Config() 
        c = screen.get_best_config(c)
    return c

class Canvas(list, Prototype, EventHandler):

    def __init__(self, width=640, height=480, name="NodeBox for OpenGL", resizable=False, border=True, settings=OPTIMAL, vsync=True):
        """ The main application window containing the drawing canvas.
            It is opened when Canvas.run() is called.
            It is a collection of drawable Layer objects, and it has its own draw() method.
            This method must be overridden with your own drawing commands, which will be executed each frame.
            Event handlers for keyboard and mouse interaction can also be overriden.
            Events will be passed to layers that have been appended to the canvas.
        """
        window = dict(
              caption = name,
              visible = False,
                width = width,
               height = height,
            resizable = resizable,
                style = border is False and WINDOW_BORDERLESS or WINDOW_DEFAULT,
               config = _configure(settings),
                vsync = vsync
        )
        Prototype.__init__(self)
        EventHandler.__init__(self)
        self.profiler                 = Profiler(self)
        self._window                  = pyglet.window.Window(**window)
        self._fps                     = None        # Frames per second.
        self._frame                   = 60          # The current frame.
        self._elapsed                 = 0           # dt = time elapsed since last frame.
        self._active                  = False       # Application is running?
        self.paused                   = False       # Pause animation?
        self._mouse                   = Mouse(self) # The mouse cursor location. 
        self._keys                    = Keys(self)  # The keys pressed on the keyboard.
        self._focus                   = None        # The layer being focused by the mouse.
        # Mouse and keyboard events:
        self._window.on_mouse_enter   = self._on_mouse_enter
        self._window.on_mouse_leave   = self._on_mouse_leave
        self._window.on_mouse_motion  = self._on_mouse_motion
        self._window.on_mouse_press   = self._on_mouse_press
        self._window.on_mouse_release = self._on_mouse_release
        self._window.on_mouse_drag    = self._on_mouse_drag
        self._window.on_mouse_scroll  = self._on_mouse_scroll
        self._window.on_key_pressed   = False
        self._window.on_key_press     = self._on_key_press
        self._window.on_key_release   = self._on_key_release
        self._window.on_text          = self._on_text
        self._window.on_text_motion   = self._on_text_motion
        self._window.on_move          = self._on_move
        self._window.on_resize        = self._on_resize
        self._window.on_close         = self.stop

    def _get_name(self):
        return self._window.caption
    def _set_name(self, str):
        self._window.set_caption(str)
        
    name = property(_get_name, _set_name)

    def _get_vsync(self):
        return self._window.vsync
    def _set_vsync(self, bool):
        self._window.set_vsync(bool)
        
    vsync = property(_get_vsync, _set_vsync)

    @property
    def layers(self):
        return self

    def insert(self, index, layer):
        list.insert(self, index, layer)
        layer.__dict__["canvas"] = self
    def append(self, layer):
        list.append(self, layer)
        layer.__dict__["canvas"] = self
    def extend(self, layers):
        for layer in layers:
            self.append(layer)
    def remove(self, layer):
        list.remove(self, layer)
        layer.__dict__["canvas"] = None
    def pop(self, index):
        layer = list.pop(index)
        layer.__dict__["canvas"] = None
        return layer
        
    def _get_x(self):
        return self._window.get_location()[0]
    def _set_x(self, v):
        self._window.set_location(v, self.y)
    def _get_y(self):
        return self._window.get_location()[1]
    def _set_y(self, v):
        self._window.set_location(self.x, v)
    def _get_xy(self):
        return (self.x, self.y)
    def _set_xy(self, (x,y)):
        self.x = x
        self.y = y
    def _get_width(self):
        return self._window.width
    def _get_height(self):
        return self._window.height
    def _get_size(self):
        return (self.width, self.height)
    def _set_width(self, v):
        self._window.width = v
    def _set_height(self, v):
        self._window.height = v
    def _set_size(self, (w,h)):
        self.width  = w
        self.height = h
    
    x      = property(_get_x, _set_x)
    y      = property(_get_y, _set_y)
    xy     = property(_get_xy, _set_xy)
    width  = property(_get_width, _set_width)
    height = property(_get_height, _set_height)
    size   = property(_get_size, _set_size)

    def _get_fullscreen(self):
        return self._window.fullscreen
    def _set_fullscreen(self, mode=True):
        self._window.set_fullscreen(mode)
        
    fullscreen = property(_get_fullscreen, _set_fullscreen)
    
    @property
    def screen(self):
        return pyglet.window.get_platform().get_default_display().get_default_screen()

    @property
    def frame(self):
        """ Yields the current frame number.
        """
        return self._frame

    @property
    def elapsed(self):
        """ Yields the elapsed time since last frame.
        """
        return self._elapsed
        
    dt = elapsed

    @property
    def mouse(self):
        """ Yields a Point(x, y) with the mouse position on the canvas.
        """
        return self._mouse
    
    @property
    def keys(self):
        return self._keys
        
    @property # Backwards compatibility.
    def key(self):
        return self._keys
        
    @property
    def focus(self):
        return self._focus
        
    #--- Event dispatchers ------------------------------
    # First events are dispatched, then update() and draw() are called.
    
    def layer_at(self, x, y, **kwargs):
        """ Find the topmost layer at the specified coordinates.
            This method returns None if no layer was found.
        """
        for layer in reversed(self):
            layer = layer.layer_at(x, y, **kwargs)
            if layer is not None:
                return layer
        return None

    def _on_mouse_enter(self, x, y):
        self._mouse.x = x
        self._mouse.y = y
        self.on_mouse_enter(self._mouse)
        
    def _on_mouse_leave(self, x, y):
        self._mouse.x = x
        self._mouse.y = y
        self.on_mouse_leave(self._mouse)
        # When the mouse leaves the canvas, no layer has the focus.
        if self._focus is not None:
            self._focus.on_mouse_leave(self._mouse)
            self._focus.focus   = False
            self._focus.pressed = False
            self._focus.dragged = False
            self._focus = None
        
    def _on_mouse_motion(self, x, y, dx, dy):
        self._mouse.x  = x
        self._mouse.y  = y
        self._mouse.dx = int(dx)
        self._mouse.dy = int(dy)
        self.on_mouse_motion(self._mouse)
        # Get the topmost layer over which the mouse is hovering.
        layer = self.layer_at(x, y, enabled=True)
        # If the layer differs from the layer which currently has the focus,
        # or the mouse is not over any layer, remove the current focus.
        if self._focus is not None and (self._focus != layer or not self._focus.contains(x,y)):
            self._focus.on_mouse_leave(self._mouse)
            self._focus.focus = False
            self._focus = None
        # Set the focus.
        if self.focus != layer and layer is not None:
            self._focus = layer
            self._focus.focus = True
            self._focus.on_mouse_enter(self._mouse)
        # Propagate mouse motion to layer with the focus.
        if self._focus is not None:
            self._focus.on_mouse_motion(self._mouse)
    
    def _on_mouse_press(self, x, y, button, modifiers):
        self._mouse.pressed   = True
        self._mouse.button    = button
        self._mouse.modifiers = [a for (a,b) in (
              (CTRL, pyglet.window.key.MOD_CTRL), 
             (SHIFT, pyglet.window.key.MOD_SHIFT), 
            (OPTION, pyglet.window.key.MOD_OPTION)) if modifiers & b]
        self.on_mouse_press(self._mouse)
        # Propagate mouse clicking to the layer with the focus.
        if self._focus is not None:
            self._focus.pressed = True
            self._focus.on_mouse_press(self._mouse)
        
    def _on_mouse_release(self, x, y, button, modifiers):
        if self._focus is not None:
            self._focus.on_mouse_release(self._mouse)
            self._focus.pressed = False
            self._focus.dragged = False
        self.on_mouse_release(self._mouse)
        self._mouse.button    = None
        self._mouse.modifiers = []
        self._mouse.pressed   = False
        self._mouse.dragged   = False
        if self._focus is not None:
            # Get the topmost layer over which the mouse is hovering.
            layer = self.layer_at(x, y, enabled=True)
            # If the mouse is no longer over the layer with the focus
            # (this can happen after dragging), remove the focus.
            if self._focus != layer or not self._focus.contains(x,y):
                self._focus.on_mouse_leave(self._mouse)
                self._focus.focus = False
                self._focus = None
            # Propagate mouse to the layer with the focus.
            if self._focus != layer and layer is not None:
                layer.focus = True
                layer.on_mouse_enter(self._mouse)
            self._focus = layer

    def _on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self._mouse.dragged   = True
        self._mouse.x         = x
        self._mouse.y         = y
        self._mouse.dx        = int(dx)
        self._mouse.dy        = int(dy)
        self._mouse.modifiers = [a for (a,b) in (
              (CTRL, pyglet.window.key.MOD_CTRL), 
             (SHIFT, pyglet.window.key.MOD_SHIFT), 
            (OPTION, pyglet.window.key.MOD_OPTION)) if modifiers & b]
        # XXX also needs to log buttons.
        self.on_mouse_drag(self._mouse)
        # Propagate mouse dragging to the layer with the focus.
        if self._focus is not None:
            self._focus.dragged = True
            self._focus.on_mouse_drag(self._mouse)
            
    def _on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self._mouse.scroll.x = scroll_x
        self._mouse.scroll.y = scroll_y
        self.on_mouse_scroll(self._mouse)
        # Propagate mouse scrolling to the layer with the focus.
        if self._focus is not None:
            self._focus.on_mouse_scroll(self._mouse)

    def _on_key_press(self, keycode, modifiers):
        self._keys.pressed = True            
        self._keys.append(keycode)
        if self._keys.code == TAB:
            self._keys.char = "\t"
        # The event is delegated in _update():
        self._window.on_key_pressed = True

    def _on_key_release(self, keycode, modifiers):
        for layer in self:
            layer.on_key_release(self.key)
        self.on_key_release(self.key)
        self._keys.char = ""
        self._keys.remove(keycode)
        self._keys.pressed = False

    def _on_text(self, text):
        self._keys.char = text
        # The event is delegated in _update():
        self._window.on_key_pressed = True
            
    def _on_text_motion(self, keycode):
        self._keys.char = ""
        # The event is delegated in _update():
        self._window.on_key_pressed = True
        
    def _on_move(self, x, y):
        self.on_move()
    
    def _on_resize(self, width, height):
        pyglet.window.Window.on_resize(self._window, width, height)
        self.on_resize()

    # Event methods are meant to be overridden or patched with Prototype.set_method().
    def on_key_press(self, keys):
        """ The default behavior of the canvas:
            - ESC exits the application,
            - CTRL-P pauses the animation,
            - CTRL-S saves a screenshot.
        """
        if keys.code == ESCAPE:
            self.stop()
        if keys.code == "p" and CTRL in keys.modifiers:
            self.paused = not self.paused
        if keys.code == "s" and CTRL in keys.modifiers:
            self.save("nodebox-%s.png" % str(datetime.now()).split(".")[0].replace(" ","-").replace(":","-"))
    
    def on_move(self):
        pass

    def on_resize(self):
        pass

    #--- Main loop --------------------------------------
        
    def setup(self):
        pass
        
    def update(self):
        pass
        
    def draw(self):
        self.clear()
        
    def draw_overlay(self):
        """ Override this method to draw once all the layers have been drawn.
        """
        pass
        
    draw_over = draw_overlay

    def _setup(self):
        # Set the window color, this will be transparent in saved images.
        glClearColor(VERY_LIGHT_GREY, VERY_LIGHT_GREY, VERY_LIGHT_GREY, 0)
        # Reset the transformation state.
        # Most of this is already taken care of in Pyglet.
        #glMatrixMode(GL_PROJECTION)
        #glLoadIdentity()
        #glOrtho(0, self.width, 0, self.height, -1, 1)
        #glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        # Enable line anti-aliasing.
        glEnable(GL_LINE_SMOOTH)
        # Enable alpha transparency.
        glEnable(GL_BLEND)
        glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA)
        #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # Start the application (if not already running).
        if not self._active:
            self._window.switch_to()
            self._window.dispatch_events()
            self._window.set_visible()
            self._active = True
        self.clear()
        self.setup()

    def _draw(self, lapse=0):
        """ Draws the canvas and its layers.
            This method gives the same result each time it gets drawn; only _update() advances state.
        """
        if self.paused: 
            return
        self._window.switch_to()
        glPushMatrix()
        self.draw()
        glPopMatrix()
        glPushMatrix()
        for layer in self:
            layer._draw()
        glPopMatrix()
        glPushMatrix()
        self.draw_overlay()
        glPopMatrix()

    def _update(self, lapse=0):
        """ Updates the canvas and its layers.
            This method does not actually draw anything, it only updates the state.
        """
        self._elapsed = lapse
        if not self.paused:
            # Advance the animation by updating all layers.
            # This is only done when the canvas is not paused.
            # Events will still be propagated during pause.
            global TIME; TIME = time()
            self._frame += 1
            self.update()
            for layer in self:
                layer._update()
        if self._window.on_key_pressed is True:
            # Fire on_key_press() event,
            # which combines _on_key_press(), _on_text() and _on_text_motion().
            self._window.on_key_pressed = False
            self.on_key_press(self._keys)
            for layer in self:
                layer.on_key_press(self._keys)
                
    def stop(self):
        # If you override this method, don't forget to call Canvas.stop() to exit the app.
        # Any user-defined stop method, added with canvas.set_method() or canvas.run(stop=stop), 
        # is called first.
        try: self._user_defined_stop()
        except:
            pass
        for f in (self._update, self._draw):
            pyglet.clock.unschedule(f)
        self._window.close()
        self._active = False
        pyglet.app.exit()

    def clear(self):
        """ Clears the previous frame from the canvas.
        """
        glClear(GL_COLOR_BUFFER_BIT)
        glClear(GL_DEPTH_BUFFER_BIT)
        glClear(GL_STENCIL_BUFFER_BIT)
    
    def run(self, draw=None, setup=None, update=None, stop=None):
        """ Opens the application windows and starts drawing the canvas.
            Canvas.setup() will be called once during initialization.
            Canvas.draw() and Canvas.update() will be called each frame. 
            Canvas.clear() needs to be called explicitly to clear the previous frame drawing.
            Canvas.stop() closes the application window.
            If the given setup, draw or update parameter is a function,
            it overrides that canvas method.
        """
        if isinstance(setup, FunctionType):
            self.set_method(setup, name="setup")
        if isinstance(draw, FunctionType):
            self.set_method(draw, name="draw")
        if isinstance(update, FunctionType):
            self.set_method(update, name="update")
        if isinstance(stop, FunctionType):
            self.set_method(stop, name="stop")
        self._frame += 1
        self._setup()
        self.fps = self._fps # Schedule the _update and _draw events.
        pyglet.app.run()

    @property
    def active(self):
        return self._active
    
    def _get_fps(self):
        return self._fps
    def _set_fps(self, v):
        # Use pyglet.clock to schedule _update() and _draw() events.
        # The clock will then take care of calling them enough times.
        # Note: frames per second is related to vsync. 
        # If the vertical refresh rate is about 30Hz you'll get top speed of around 33fps.
        # It's probably a good idea to leave vsync=True if you don't want to fry the GPU.
        for f in (self._update, self._draw):
            pyglet.clock.unschedule(f)
            if v is None:
                pyglet.clock.schedule(f)
            if v > 0:
                pyglet.clock.schedule_interval(f, 1.0/v)
        self._fps = v
        
    fps = property(_get_fps, _set_fps)        

    #--- Frame export -----------------------------------

    def render(self):
        """ Returns a screenshot of the current frame as a texture.
            This texture can be passed to the image() command.
        """
        return pyglet.image.get_buffer_manager().get_color_buffer().get_texture()
        
    buffer = screenshot = render
    
    @property
    def texture(self):
        return pyglet.image.get_buffer_manager().get_color_buffer().get_texture()

    def save(self, path):
        """ Exports the current frame as a PNG-file.
        """
        pyglet.image.get_buffer_manager().get_color_buffer().save(path)

    #--- Prototype --------------------------------------

    def __setattr__(self, k, v):
        # Canvas is a Prototype, so Canvas.draw() can be overridden 
        # but it can also be patched with Canvas.set_method(draw).
        # Specific methods (setup, draw, mouse and keyboard events) can also be set directly
        # (e.g. canvas.on_mouse_press = my_mouse_handler).
        # This way we don't have to explain set_method() to beginning users..
        if isinstance(v, FunctionType) and (k in ("setup", "draw", "update", "stop") \
        or k.startswith("on_") and k in (
            "on_mouse_enter",
            "on_mouse_leave",
            "on_mouse_motion",
            "on_mouse_press",
            "on_mouse_release",
            "on_mouse_drag",
            "on_mouse_scroll",
            "on_key_press",
            "on_key_release",
            "on_move",
            "on_resize")):
            self.set_method(v, name=k)
        else:
            object.__setattr__(self, k, v)
            
    def set_method(self, function, name=None):
        if name == "stop" \
        or name is None and function.__name__ == "stop":
            Prototype.set_method(self, function, name="_user_defined_stop") # Called from Canvas.stop().
        else:
            Prototype.set_method(self, function, name)
            
    def __repr__(self):
        return "Canvas(name='%s', size='%s', layers=%s)" % (self.name, self.size, repr(list(self)))

#--- PROFILER ----------------------------------------------------------------------------------------

CUMULATIVE = "cumulative"
SLOWEST    = "slowest"

_profile_canvas = None
_profile_frames = 100
def profile_run():
    for i in range(_profile_frames):
        _profile_canvas._update()
        _profile_canvas._draw()

class Profiler:
    
    def __init__(self, canvas):
        self.canvas  = canvas
    
    @property
    def framerate(self):
        return pyglet.clock.get_fps()
    
    def run(self, draw=None, setup=None, update=None, frames=100, sort=CUMULATIVE, top=30):
        """ Runs cProfile on the canvas for the given number of frames.
            The performance statistics are returned as a string, sorted by SLOWEST or CUMULATIVE.
            For example, instead of doing canvas.run(draw):
            print canvas.profiler.run(draw, frames=100)
        """
        # Register the setup, draw, update functions with the canvas (if given).
        if isinstance(setup, FunctionType):
            self.canvas.set_method(setup, name="setup")
        if isinstance(draw, FunctionType):
            self.canvas.set_method(draw, name="draw")
        if isinstance(update, FunctionType):
            self.canvas.set_method(update, name="update")
        # If enabled, turn Psyco off.
        psyco_stopped = False
        try: 
            psyco.stop()
            psyco_stopped = True
        except:
            pass
        # Set the current canvas and the number of frames to profile.
        # The profiler will then repeatedly execute canvas._update() and canvas._draw().
        # Statistics are redirected from stdout to a temporary file.
        global _profile_canvas, _profile_frames
        _profile_canvas = self.canvas
        _profile_frames = frames
        import cProfile
        import pstats
        cProfile.run("profile_run()", "_profile")
        p = pstats.Stats("_profile")
        p.stream = open("_profile", "w")
        p.sort_stats(sort==SLOWEST and "time" or sort).print_stats(top)
        p.stream.close()
        s = open("_profile").read()
        remove("_profile")
        # Restart Psyco if we stopped it.
        if psyco_stopped:
            psyco.profile()
        return s

#--- LIBRARIES ---------------------------------------------------------------------------------------
# Import the library and assign it a _ctx variable containing the current context.
# This mimics the behavior in NodeBox for Mac OS X.

def ximport(library):
    from sys import modules
    library = __import__(library)
    library._ctx = modules[__name__]
    return library

#-----------------------------------------------------------------------------------------------------
# Linear interpolation math for BezierPath.point() etc.

import bezier
