# NodeBox for OpenGL Painter
# Authors: Frederik De Bleser, Tom De Smedt
# License: GPL (see LICENSE.txt for details).
# Copyright (c) 2008 City In A Bottle (cityinabottle.org)

# All graphics are drawn directly to the screen.
# No scenegraph is kept for obvious performance reasons (therefore, no canvas._grobs as in NodeBox).

from pyglet.gl import *
from pyglet import image  as pyglet_image
from pyglet import font   as pyglet_font
from pyglet import window as pyglet_window

from math import cos, sin, pi, floor
from time import time
from random import choice, shuffle, random as rnd
from new import instancemethod
from glob import glob
from os.path import basename
from StringIO import StringIO

#import bezier
# XXX - Do this at the end, when we have defined BezierPath, which is needed in the bezier module.

#=====================================================================================================

#--- COLOR -------------------------------------------------------------------------------------------

_background = None
_fill = None
_stroke = None
_strokewidth = None

class Color(list):

    def __init__(self, *a, **kwargs):
        """ A color with R, G, B, A properties (0.0-1.0).
        """
        # Values are supplied as a tuple.
        if len(a) == 1 and isinstance(a[0], (list, tuple)):
            a = a[0]
        # R, G, B and A.
        if len(a) == 4:
            r, g, b, a = a[0], a[1], a[2], a[3]
        # R, G and B.
        elif len(a) == 3:
            r, g, b, a = a[0], a[1], a[2], 1
        # Two values, grayscale and alpha.
        elif len(a) == 2:
            r, g, b, a = a[0], a[0], a[0], a[1]
        # One value, another color object.
        elif len(a) == 1 and isinstance(a[0], Color):
            r, g, b, a = a[0].r, a[0].g, a[0].b, a[0].a
        # One value, grayscale.
        elif len(a) == 1:
            r, g, b, a = a[0], a[0], a[0], 1
        # No values or None, transparent black.
        elif len(a) == 0 or (len(a) == 1 and a[0] == None):
            r, g, b, a = 0, 0, 0, 0
        self.base = float(kwargs.get("base", 1.0))
        list.__init__(self, [r/self.base, g/self.base, b/self.base, a/self.base])

    def _get_r(self): return self[0]
    def _get_g(self): return self[1]
    def _get_b(self): return self[2]
    def _get_a(self): return self[3]
    
    def _set_r(self, v): self[0] = v
    def _set_g(self, v): self[1] = v
    def _set_b(self, v): self[2] = v
    def _set_a(self, v): self[3] = v
    
    r = property(_get_r, _set_r)
    g = property(_get_g, _set_g)
    b = property(_get_b, _set_b)
    a = property(_get_a, _set_a)

    def copy(self):
        return Color(self)

    def _apply(self):
        glColor4f(self[0], self[1], self[2], self[3])

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

color = Color

def background(*a):
    """ Sets the current window background color.
    """
    global _background
    _background = color(*a)
    glClearColor(_background.r, _background.g, _background.b, _background.a)
    return _background

def fill(*a):
    """ Sets the current fill color for drawing primitives and paths.
    """
    global _fill
    _fill = color(*a)
    return _fill

fill(0) # default fill is black

def stroke(*a):
    """ Sets the current stroke color.
    """
    global _stroke
    _stroke = color(*a)
    return _stroke

def nofill():
    """ No current fill color.
    """
    global _fill
    _fill = None

def nostroke():
    """ No current stroke colors
    """
    global _stroke
    _stroke = None

# Note: thick strokewidth results in ugly (i.e. no) line caps.
def strokewidth(width=None):
    """ Sets the outline width.
    """
    global _strokewidth
    if width != None:
        _strokewidth = width
        glLineWidth(width)
    return _strokewidth

def outputmode(mode=None):
    raise NotImplementedError

def colormode(mode=None, range=1.0):
    raise NotImplementedError

#--- COLORSPACE --------------------------------------------------------------------------------------
# Hue, Saturation, Brightness model.

def rgba(h, s, v, a):
    """ Converts the given H,S,B color values to R,G,B.
    """
    if s == 0: 
        return v, v, v
    h = h / (60.0/360)
    i = floor(h)
    f = h - i
    p = v * (1-s)
    q = v * (1-s * f)
    t = v * (1-s * (1-f))
    if i > 4:
        return v, p, q, a
    return [(v,t,p,a), (q,v,p,a), (p,v,t,a), (p,q,v,a), (t,p,v,a)][int(i)]

def hsba(r, g, b, a):
    """ Converts the given R,G,B values to H,S,B.
    """
    h, s, v = 0, 0, max(r, g, b)
    d = v - min(r, g, b)
    if v != 0:
        s = d / float(v)
    if s != 0:
        if   r == v: h = 0 + (g-b) / d
        elif g == v: h = 2 + (b-r) / d
        else       : h = 4 + (r-g) / d
    h = h * (60.0/360)
    if h < 0: 
        h = h + 1.0
    return h, s, v, a

def darker(clr, step=0.2):
    """ Returns a copy of the color with a darker brightness.
    """
    h, s, b, a = hsba(clr[0], clr[1], clr[2], clr[3])
    b = max(0, b-step)
    return color(rgb(h,s,b,a))

def lighter(clr, step=0.2):
    """ Returns a copy of the color with a lighter brightness.
    """
    h, s, b, a = hsba(clr[0], clr[1], clr[2], clr[3])
    b = min(1, b+step)
    return color(rgb(h,s,b,a))

#--- COLOR MIXIN -------------------------------------------------------------------------------------
# Drawing commands like rect() have optional parameters fill and stroke to set the color directly.

def color_mixin(**kwargs):
    fill   = kwargs.get("fill", _fill)
    stroke = kwargs.get("stroke", _stroke)
    return (fill, stroke)   

#--- GRADIENT ----------------------------------------------------------------------------------------

def gradient(x, y, width, height, *a):
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
        clr1 = clr2 = Color(0,0,0,1)
        clr3 = clr4 = Color(1,1,1,1)
    glPushMatrix()
    glTranslatef(x, y, 0)
    glScalef(width, height, 1)
    glBegin(GL_QUADS)
    clr1 = Color(clr1)
    clr2 = Color(clr2)
    clr3 = Color(clr3)
    clr4 = Color(clr4)
    clr1._apply(); glVertex2f(-0.0,  1.0)
    clr2._apply(); glVertex2f( 1.0,  1.0)
    clr3._apply(); glVertex2f( 1.0, -0.0)
    clr4._apply(); glVertex2f(-0.0, -0.0)
    glEnd()
    glPopMatrix()

#=====================================================================================================

#--- TRANSFORMATIONS ---------------------------------------------------------------------------------
# Unlike NodeBox, all transformations are CORNER-mode and originate from the bottom-left corner.

def push():
    glPushMatrix()

def pop():
    glPopMatrix()

def translate(x, y, z=0):
    glTranslatef(x, y, z)

def rotate(degrees, x=0, y=0, z=1):
    glRotatef(degrees, x, y, z)

def scale(x, y=None, z=1):
    if y == None: 
        y = x
    glScalef(x, y, z)

def reset():
    """ Resets the transform state of the layer or canvas.
    """
    glPopMatrix()
    glPushMatrix()

def transform(mode=None):
    raise NotImplementedError
    
def skew(x, y, z=0):
    raise NotImplementedError

#--- PRIMITIVES --------------------------------------------------------------------------------------
# Point, line, rect, ellipse, arrow.

class Point:
    
    def __init__(self, x, y, z=0):
        self.x = x
        self.y = y
        self.z = z
        
    def __repr__(self):
        return "Point(x=%.2f, y=%.2f, z=%.2f)" % (self.x, self.y, self.z)
        
    def __eq__(self, pt):
        if not isinstance(pt, Point): return False
        return self.x == pt.x \
           and self.y == pt.y \
           and self.z == pt.z
    
    def __ne__(self, pt):
        return not self.__eq__(pt)

def line(x0, y0, x1, y1, **kwargs):
    """ Draws a straight line from x0, y0 to x1, y1 with the current stroke color.
    """
    fill, stroke = color_mixin(**kwargs)
    if stroke != None:
        stroke._apply()
        glBegin(GL_LINE_LOOP)
        glVertex2f(x0, y0)
        glVertex2f(x1, y1)
        glEnd()

def rect(x, y, width, height, **kwargs):
    """ Draws a rectangle with bottom left corner at x, y.
    The current stroke and fill color are applied.
    """
    fill, stroke = color_mixin(**kwargs)
    for i, clr in enumerate((fill, stroke)):
        if clr != None:
            clr._apply()
            glBegin((GL_POLYGON, GL_LINE_LOOP)[i])
            glVertex2f(x, y)
            glVertex2f(x+width, y)
            glVertex2f(x+width, y+height)
            glVertex2f(x, y+height)
            glEnd()

_ellipse_cache = {}
def ellipse(x, y, width, height, segments=50, **kwargs):
    """ Draws an ellipse with center located at x, y.
    The current stroke and fill color are applied.
    """
    if not segments in _ellipse_cache:
        # Cache both a filled and outlined ellipse for the given number of segments.
        _ellipse_cache[segments] = []
        for mode in ((GL_POLYGON, GL_LINE_LOOP)):
            path = glGenLists(1)
            glNewList(path, GL_COMPILE)
            glBegin(mode);
            for i in range(segments):
                t = 2*pi * float(i)/segments
                glVertex2f(cos(t)*0.5, sin(t)*0.5);
            glEnd();
            glEndList()
            _ellipse_cache[segments].append(path)
        paths = _ellipse_cache[segments]
    fill, stroke = color_mixin(**kwargs)
    for i, clr in enumerate((fill, stroke)):
        if clr != None:
            clr._apply()
            path = _ellipse_cache[segments][i]
            glPushMatrix()
            glTranslatef(x, y, 0)
            glScalef(width, height, 1)
            glCallList(path)
            glPopMatrix()

oval = ellipse # backwards compatibility

def arrow(x, y, width, **kwargs):
    """ Draws an arrow with its tip located at x, y.
    """
    head = width * 0.4
    tail = width * 0.2
    fill, stroke = color_mixin(**kwargs)
    for i, clr in enumerate((fill, stroke)):
        if clr != None:
            clr._apply()
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
    raise NotImplementedError
    
#--- RECTANGLE ---------------------------------------------------------------------------------------
# The rect class is used for calculating intersections between rectangles and to store
# bounding information.

class Rect(object):
    
    def __init__(self, x=0.0, y=0.0, width=0.0, height=0.0):
        self.x, self.y, self.width, self.height = float(x), float(y), float(width), float(height)
        
    def _is_empty(self):
        r = self.normalized()
        return r.width <= 0.0 or r.height <= 0.0
    is_empty = property(_is_empty)
        
    def normalized(self):
        r = copy(self)
        if r.width < 0:
            r.x += r.width
            r.width = -r.width
        if r.height < 0:
            r.y += r.height
            r.height = -r.height
        return r
        
    def united(self, r):
        r1 = self.normalized()
        r2 = r.normalized()
        u = Rect()
        u.x = min(r1.x, r2.x)
        u.y = min(r1.y, r2.y)
        u.width = max(r1.x + r1.width, r2.x + r2.width) - u.x
        u.height = max(r1.y + r1.height, r2.y + r2.height) - u.y
        return u
        
    def intersects(self, r):
        r1 = self.normalized()
        r2 = r.normalized()
        return max(r1.x, r2.x) < min(r1.x + r1.width, r2.x + r2.width) and \
               max(r1.y, r2.y) < min(r1.y + r1.height, r2.y + r2.height)

    def contains(self, obj):
        if isinstance(obj, Point):
            r = self.normalized()
            return obj.x >= r.x and obj.x <= r.x + r.width and \
                   obj.y >= r.y and obj.y <= r.y + r.height
        elif isinstance(obj, Rect):
            r1 = self.normalized()
            r2 = obj.normalized()
            return r2.x >= r1.x and r2.x + r2.width <= r1.x + r1.width and \
                   r2.y >= r1.y and r2.y + r2.height <= r1.y + r1.height
            
    def __eq__(self, r):
        if not isinstance(r, Rect): return False
        return self.x == r.x \
           and self.y == r.y \
           and self.width == r.width \
           and self.height == r.height
           
    def __repr__(self):
        return "Rect(%.1f, %.1f, %.1f, %.1f)" % (self.x, self.y, self.width, self.height)
        
    def __copy__(self):
        return Rect(self.x, self.y, self.width, self.height)

#--- PATH --------------------------------------------------------------------------------------------
# A BezierPath class with lineto(), curveto() and moveto() commands.
# It has all the path math functionality from NodeBox and a ray casting algorithm for contains().

MOVETO  = "moveto"
LINETO  = "lineto"
CURVETO = "curveto"
CLOSE   = "close"

CURVE_SEGMENTS = 30 # the number of line segments a curve is made up of.

class PathError(Exception): pass
class NoCurrentPointForPath(Exception): pass
class NoCurrentPath(Exception): pass

class PathElement:
    
    def __init__(self, cmd, x, y, vx1, vy1, vx2, vy2, segments=CURVE_SEGMENTS):
        # XXX - the parameters differ from PathElement in NodeBox.
        self.cmd = cmd
        self.x = x
        self.y = y
        self.ctrl1 = Point(vx1, vy1)
        self.ctrl2 = Point(vx2, vy2)
        self._segments = segments
    
    def copy(self):
        return PathElement(
            self.cmd, 
            self.x, 
            self.y, 
            self.ctrl1.x, 
            self.ctrl1.y, 
            self.ctrl2.x, 
            self.ctrl2.y, 
            self._segments
        )
    
    def __eq__(self, pt):
        if not isinstance(pt, PathElement): return False
        return self.cmd == pt.cmd \
           and self.x == pt.x \
           and self.y == pt.y \
           and self.ctrl1 == pt.ctrl1 \
           and self.ctrl2 == pt.ctrl2 \
           and self._segments == pt._segments
        
    def __ne__(self, pt):
        return not self.__eq__(pt)

class BezierPath(list):
    
    def __init__(self, path=None, **kwargs):
        if isinstance(path, (list, tuple)):
            self.extend(path)
        elif isinstance(path, BezierPath):
            self.extend([pt.copy() for pt in path])
        self._kwargs = kwargs
        self._segment_cache = None
    
    def copy(self):
        return BezierPath(self, **self._kwargs)
    
    def moveto(self, x, y):
        """ Add a new point to the path at x, y.
        """
        self._segment_cache = None
        self.append(PathElement(MOVETO, x, y, x, y, x, y))
    
    def lineto(self, x, y):
        """ Add a line from the previous point to x, y.
        """
        self._segment_cache = None
        self.append(PathElement(LINETO, x, y, x, y, x, y))
        
    def curveto(self, x1, y1, x2, y2, x3, y3, segments=CURVE_SEGMENTS):
        """ Add a Bezier-curve from the previous to x3, y3.
        The curvature is determined by control handles x1, y1 and x2, y2.
        """
        self._segment_cache = None
        self.append(PathElement(CURVETO, x3, y3, x1, y1, x2, y2, segments))
    
    def closepath(self):
        """ Add a line from the previous point to the last MOVETO.
        """
        self._segment_cache = None
        self.append(PathElement(CLOSE, 0, 0, 0, 0, 0, 0))
    
    def _draw_line(self, x0, y0, x1, y1):
        glVertex2f(x0, y0)
        glVertex2f(x1, y1)
    
    def _draw_curve(self, x0, y0, x1, y1, x2, y2, x3, y3, segments=CURVE_SEGMENTS):
        # Curves are interpolated from a number of straight line segments.
        xi, yi = x0, y0
        for i in range(segments):
            xj, yj, vx1, vy1, vx2, vy2 = bezier.curvepoint(float(i)/segments, x0, y0, x1, y1, x2, y2, x3, y3)
            glVertex2f(xi, yi)
            glVertex2f(xj, yj)
            xi, yi = xj, yj
    
    def draw(self, **kwargs):
        fill, stroke = color_mixin(**self._kwargs)
        for i, clr in enumerate((fill, stroke)):
            if clr != None:
                clr._apply()
                glBegin((GL_POLYGON, GL_LINE_STRIP)[i])
                x0, y0 = None, None
                closeto = None
                for pt in self:
                    if (pt.cmd == LINETO or pt.cmd == CURVETO) and x0 == y0 == None:
                        raise NoCurrentPointForPathError
                    elif pt.cmd == LINETO:
                        self._draw_line(x0, y0, pt.x, pt.y)
                    elif pt.cmd == CURVETO:
                        self._draw_curve(x0, y0, pt.ctrl1.x, pt.ctrl1.y, pt.ctrl2.x, pt.ctrl2.y, pt.x, pt.y, pt._segments)
                    elif pt.cmd == MOVETO:
                        closeto = pt
                        glEnd() # close this contour and start the next
                        glBegin((GL_POLYGON, GL_LINE_STRIP)[i])
                    elif pt.cmd == CLOSE and closeto != None:
                        self._draw_line(x0, y0, closeto.x, closeto.y)
                    x0, y0 = pt.x, pt.y
                glEnd()

    def rect(self, x, y, width, height):
        """ Add a rectangle to the path.
        """
        self.moveto(x, y)
        self.lineto(x+width, y)
        self.lineto(x+width, y+height)
        self.lineto(x, y+height)
        self.lineto(x, y)
    
    def ellipse(self, x, y, width, height, segments=50):
        """ Add an ellipse to the path.
        """
        # Contrary to NodeBox, it is actually faster to draw each ellipse separately
        # than all of them together in a single path (path ellipses are not cached).
        w, h, s = width*0.5, height*0.5, segments/4
        k = 0.5522847498    # kappa: (-1 + sqrt(2)) / 3 * 4
        self.moveto(x, y-h) # http://www.whizkidtech.redprince.net/bezier/circle/
        self.curveto(x+w*k, y-h,   x+w,   y-h*k, x+w, y,   s)
        self.curveto(x+w,   y+h*k, x+w*k, y+h,   x,   y+h, s)
        self.curveto(x-w*k, y+h,   x-w,   y+h*k, x-w, y,   s)
        self.curveto(x-w,   y-h*k, x-w*k, y-h,   x,   y-h, s)
        self.closepath()
        
    oval = ellipse

    def point(self, t, precision=10):
        """ Calculates point at time t (0.0-1.0) on the path.
        See the linear interpolation math in bezier.py.
        """
        if self._segment_cache == None:
            self._segment_cache = bezier.length(self, segmented=True, n=precision)
        return bezier.point(self, t, segments=self._segment_cache)
    
    def points(self, amount=2, start=0.0, end=1.0):
        """ Returns a list of PathElements along the path.
        """
        # To omit the last point on closed paths: end = 1 - 1.0/amount
        n = end - start
        d = n
        if amount>1: 
            d = n / (amount-1)
        for i in range(amount):
            yield self.point(start+d*i)
    
    def addpoint(self, t):
        """ Inserts a new PathElement at time t (0.0-1.0) on the path.
        """
        self._segment_cache = None
        bezier.insert_point(self, t)
        
    split = addpoint
    
    @property 
    def length(self):
        """ Returns an approximation of the total length of the path.
        """
        return bezier.length(self, segmented=False, n=10)
    
    @property
    def contours(self):
        """ Returns a list of contours (segments separated by a MOVETO) in the path.
        """
        return bezier.contours(self)

    def contains(self, x, y, precision=100):
        """ Ray casting algorithm.
        Determines how many times a horizontal ray starting from the point 
        intersects with the sides of the polygon. 
        If it is an even number of times, the point is outside, if odd, inside.
        The algorithm does not always report correctly when the point is very close to the boundary.
        """
        odd = False
        points = list(self.points(precision))
        for i in range(len(points)):
            x0, y0 = points[i].x, points[i].y
            x1, y1 = points[(i+1)%n].x, points[(i+1)%n].y
            if (y0 < y and y1 >= y) or (y1 < y and y0 >= y):
                if x0 + (y-y0) / (y1-y0) * (x1-x0) < x:
                    odd = not odd
        return odd

    @property
    def bounds(self, precision=100):
        """ Returns a (x, y, width, height)-tuple of the approximate path dimensions.
        """
        l = t = float( "inf")
        r = b = float("-inf")
        for pt in self.points(precision):
            if pt.x < l: l = pt.x
            if pt.y < t: t = pt.y
            if pt.x > r: r = pt.x
            if pt.y > b: b = pt.y
        return l, t, r-l, b-t


def drawpath(path, **kwargs):
    """ Draws the given BezierPath (or list of PathElements).
    """
    if isinstance(path, (list, tuple)):
        path = BezierPath(path)
    path.draw(**kwargs)

_autoclosepath = True
def autoclosepath(close=False):
    global _autoclosepath
    _autoclosepath = close

_path = None
def beginpath(x, y):
    global _path
    _path = BezierPath()
    _path.moveto(x, y)

def moveto(x, y):
    if _path == None: 
        raise NoCurrentPath
    _path.moveto(x, y)

def lineto(x, y):
    if _path == None: 
        raise NoCurrentPath
    _path.lineto(x, y)

def curveto(x1, y1, x2, y2, x3, y3, segments=CURVE_SEGMENTS):
    if _path == None: 
        raise NoCurrentPath
    _path.curveto(x1, y1, x2, y2, x3, y3, segments)

def closepath():
    if _path == None: 
        raise NoCurrentPath
    _path.closepath()

def endpath(draw=True):
    global _path, _autoclosepath
    if _path == None: 
        raise NoCurrentPath
    if _autoclosepath == True:
        _path.closepath()
    if draw:
        _path.draw()
    p, _path = _path, None
    return p

def findpath(points, curvature=1.0):
    bezier.findpath(points, curvature)

def autoclosepath(close=False):
    raise NotImplementedError

def beginclip(path):
    raise NotImplementedError

def endclip():
    raise NotImplementedError

#=====================================================================================================

#--- IMAGE -------------------------------------------------------------------------------------------
# Caching, drawing, pixels, offscreen buffer and filters.

pow2 = [2**n for n in range(20)]
def ceil2(x):
    """ Returns the nearest power of 2 that is higher than x, e.g. 700 => 1024.
    """
    for y in pow2:
        if y >= x:
            return y

class ImageError(Exception): pass

_image_cache = {}
def load_image(img, data=None):
    """ Returns a (cached) texture based on the given image filename, Pixel object, byte data.
    If the given image is already a texture, simply return it.
    """
    # Image texture stored in cache, referenced by file path.
    if isinstance(img, str) and img in _image_cache:
        return _image_cache[img]
    # Image texture, return original.
    elif isinstance(img, pyglet_image.Texture):
        return img
    # Pixels object, return pixel texture.
    elif isinstance(img, Pixels):
        return img.texture
    # Image file path, load it, cache it, return texture.
    elif isinstance(img, str):
        _image_cache[img] = pyglet_image.load(img).get_texture()
        return _image_cache[img]
    # Image data as byte string, load it, return texture.
    elif isinstance(data, str):
        return pyglet_image.load(None, file=StringIO(data)).get_texture()
    # Don't know how to handle this image.
    raise ImageError, "unknown image "+str(img.__class__)

def cache(img, id):
    """ Store the given image in cache, referenced by id (which can then be passed to image()).
    This is useful for procedurally rendered images (which are not stored in cache by default).
    """
    _image_cache[id] = img
    return img

def image(img, x=0, y=0, width=None, height=None, 
          alpha=1.0, color=(1,1,1), quad=(0,0,0,0,0,0,0,0), filter=None, data=None, draw=True):
    """ Draws the image at x, y, scaling it to the given with and height.
    The image's transparency can be set with alpha (0.0-1.0).
    Applies the given color adjustment, quad distortion and filter (one filter can be specified).
    """
    img = load_image(img, data)
    if draw:
        t = img.tex_coords # power-2 dimensions
        w = img.width      # see Pyglet programming guide -> OpenGL imaging
        h = img.height
        if width != None: 
            w += width-w
        if height != None: 
            h += height-h
        dx1, dy1, dx2, dy2, dx3, dy3, dx4, dy4 = quad
        if filter:
            filter.image = img # register the current image with the filter
            filter.push()
        # Actual OpenGL drawing code:
        glPushMatrix()
        glTranslatef(x, y, 0)
        glColor4f(color[0], color[1], color[2], alpha)
        glEnable(img.target)
        glBindTexture(img.target, img.id)
        glBegin(GL_QUADS)
        glTexCoord3f(t[0], t[1],  t[2] ); glVertex3f(dx4,   dy4,   0)
        glTexCoord3f(t[3], t[4],  t[5] ); glVertex3f(dx3+w, dy3,   0)
        glTexCoord3f(t[6], t[7],  t[8] ); glVertex3f(dx2+w, dy2+h, 0)
        glTexCoord3f(t[9], t[10], t[11]); glVertex3f(dx1,   dy1+h, 0)
        glEnd()
        glDisable(img.target)
        glPopMatrix()
        if filter:
            filter.pop()
    return img

def imagesize(img):
    """ Returns a (width, height)-tuple with the image dimensions.
    """
    img = load_image(img)
    return (img.width, img.height)

def adjust(r=0, g=0, b=0):
    """ Returns a tuple with increased (>0) or decreased (<0) R,G,B intensities.
    Use this to set the image() color-parameter.
    """
    m = max(r, g, b)
    return r+1-m, g+1-m, b+1-m
    
def distort(dx1=0, dy1=0, dx2=0, dy2=0, dx3=0, dy3=0, dx4=0, dy4=0):
    """ Returns a tuple with corner offsets.
    Use this to set the image() quad-parameter.
    """
    return (dx1, dy1, dx2, dy2, dx3, dy3, dx4, dy4)

def crop(img, x=0, y=0, width=None, height=None):
    """ Returns the given (x,y,width,heigth)-region from the image.
    Use this to pass cropped image files to image().
    """
    img = load_image(img)
    if width  == None: width  = img.width
    if height == None: height = img.height
    return img.get_region(x, y, min(img.width-x, width), min(img.height-y, height))

#--- PIXELS ------------------------------------------------------------------------------------------

class Pixels(list):
    
    def __init__(self, img):
        """ A list of color values (0-255) for each pixel in the given image.
        """
        self._raw  = load_image(img).get_image_data()
        self._data = self._raw.get_data("RGBA", self._raw.width*4)
        self._texture  = None
    
    def __len__(self):
        return len(self._data) / 4
    
    def __iter__(self):
        for i in range(len(self)):
            yield self[i]
    
    def __getitem__(self, i):
        # clr = color(Pixels[i], base=255)
        # Users need to wrap the list in a Color themselves for performance.
        return self._data[i*4:i*4+4]
    
    def __setitem__(self, i, v):
        # Pixels[i] = color()
        # User is responsible for keeping channel values between 0 and 255.
        if isinstance(v, Color):
            v = [int(v[0]*255), int(v[1]*255), int(v[2]*255), int(v[3]*255)]
        for j in range(4):
            self._data[i*4+j] = v[j]
    
    def __getslice__(self, i, j):
        return [self[i+n] for n in range(j-i)]
    
    def __setslice__(self, i, j, seq):
        for n in range(j-i):
            self[i+n] = seq[n]
    
    def update(self):
        """ Pixels.update() must be called to refresh the image.
        """
        self._raw.set_data("RGBA", self._raw.width*4, self._data)
        self._texture = self._raw.get_texture()
        
    @property
    def texture(self):
        if self._texture == None:
            self.update()
        return self._texture

pixels = Pixels

#--- ANIMATION ---------------------------------------------------------------------------------------
# A sequence of images displayed in a loop.

FADE = "fade"

class Animation(list):
    
    def __init__(self, *a, **kwargs):
        if len(a) == 1 and isinstance(a[0], (list, tuple)):
            a = a[0]
        list.__init__(self, a)
        self._t = Transition(0, interpolation=kwargs.get("interpolation", LINEAR))
        self.transition = kwargs.get("transition", None) # None or FADE
        self.duration   = kwargs.get("duration", 1.0) 
    
    def copy(self):
        a = Animation(self, transition=self.transition, duration=self.duration)
        a._t = self._t.copy()
        return a
    
    def update(self, pause=False):
        """ Blend to the next image (and wait there if pause=True).
        """
        if self._t.done and not pause:
            self._t.set(self._t._v1+1, self.duration)
        self._t.update()
    
    @property
    def current(self):
        return self[self._t._v1 % len(self)]
    
    @property
    def next(self):
        return self[(self._t._v1+1) % len(self)]
        
    @property
    def time(self):
        # Elapsed transition time between two images (between 0.0 and 1.0).
        return self._t._vi-self._t._v0
    
    def draw(self, *args, **kwargs):
        image(self.current, *args, **kwargs)
        if self.transition == FADE:
            kwargs["alpha"] = self.time # XXX - transparency differs with 2 images over each other.
            image(self.next, *args, **kwargs)

animation = Animation

#--- OFFSCREEN RENDERING -----------------------------------------------------------------------------
# To draw offscreen:
#
# def draw(buffer):
#    ...
# offscreen.draw = draw
# img = offscreen.render()
#
# OR
#
# - offscreen.push()
# - drawing commands
# - offscreen.pop()
# - the graphics end up in offscreen.image, which you can pass to image() command.
#
# To change the size of the offscreen image: offscreen.width, offscreen,height = x, y
# When this happens, the offscreen buffer will create a new texture to draw in.
# The less you change about the offscreen buffer the faster it runs.
# To get a part of the offscreen image: 
# offscreen.slice(x, y, width, height).

from shader import FBO
offscreen = FBO(640, 480)

def render(img, *filters):
    """ A rendering chain that applies all the given filters on the image.
    The image is rendered offscreen and then returned.
    """
    img = load_image(img)
    if len(filters) == 1 and isinstance(filters[0], (list, tuple)):
        filters = filters[0]
    offscreen.width = img.width
    offscreen.height = img.height
    offscreen.push()
    image(img)
    for filter in filters:
        filter.image = img # filter may need some information about the current image
        filter.push()
        image(offscreen.image)
        filter.pop()
    offscreen.pop()
    return offscreen.image

#--- FILTERS -----------------------------------------------------------------------------------------
# There are three ways in which to use a filter:
# - pass as a parameter to image(): image(img, filter=blur(scale=1.0))
# - use as an offscreen command: img = blur(img, scale=1.0, n=10)
#
# OR
#
# b = blur()
# b.image = img
# b.push()
# ...
# b.pop()

from shader import FragmentShader, vec2, vec3, vec4
from shader import *

#def _get_blend_images(*a, **kwargs):
#    blend = kwargs.get("blend", None)
#    if len(a) == 1:
#        if blend == None:
#            return None, a[0]
#        else:
#            return a[0], blend
#    elif len(a) == 2:
#        return a[0], a[1]
#    else:
#        return None, blend

def blur(image=None, scale=1.0, n=1, kernel=5):
    """ Returns a blur filter (if image=None) or a rendered blurred image (if given).
    """
    filter = Blur(image, scale, kernel)
    if image: 
        return render(image, [filter for i in range(n)])
    return filter

def colorize(image=None, color=(1,1,1,1), bias=(0,0,0,0)):
    """ Returns a colorize filter (if image=None) or a rendered, colorized image (if given).
    The image's pixels are multiplied by given color, and the bias is then added.
    """
    filter = Colorize(image, color, bias)
    if image:
        return render(image, filter)
    return filter

def multiply(image=None, blend=None, opacity=1.0):
    filter = Blend("multiply", image, blend, opacity)
    if image:
        return render(image, filter)
    return filter

LINEAR = "linear"
RADIAL = "radial"
def xgradient(width, height, clr1=(0,0,0,1), clr2=(1,1,1,1), type=LINEAR):
    """ Returns a linear or radial texture of the given size.
    The gradient is rendered in a power-2 dimension image and then scaled down,
    e.g. width=700 renders a gradient in width=1024.
    Remember to cache the gradient and reuse it when possible.
    """
    if type == "radial":
        filter = RadialGradient(None, clr1, clr2)
    else:
        filter = LinearGradient(None, clr1, clr2)
    img = pyglet_image.Texture.create(ceil2(width), ceil2(height))
    offscreen.width = width
    offscreen.height = height
    offscreen.push()
    image(img, 0, 0, width, height, filter=filter)
    offscreen.pop()
    return offscreen.image
        

#=====================================================================================================

#--- TEXT --------------------------------------------------------------------------------------------

LEFT = "left"
RIGHT = "right"
CENTER = "center"

_font = None
_fontname = "Verdana"
_fontsize = 12
_lineheight = 1.0
_align = LEFT

def load_font(file):
    pyglet_font.add_file(file)

_font_cache = {}
def font(fontname=None, size=None):
    """ Sets the current font and/or fontsize.
    """
    global _font, _fontname, _fontsize
    if fontname != None:
        _fontname = fontname
    if size != None:
        _fontsize = size
    id = (_fontname, _fontsize)
    if not id in _font_cache:
        _font_cache[id] = pyglet_font.load(_fontname, _fontsize)
    _font = _font_cache[id]
    return _font
font()

def fontname(name=None):
    """ Sets the current font used when drawing text.
    """
    font(name, None)
    return _fontname

def fontsize(size=None):
    """ Sets the current fontsize.
    """
    font(None, size)
    return _fontsize

def lineheight(size=None):
    """ Sets the vertical spacing between lines of text.
    """
    global _lineheight
    if size != None:
        _lineheight = size
    return _lineheight

def align(mode=None):
    """ Sets the alignment of text paragrapgs (LEFT, RIGHT or CENTER).
    """
    global _align
    if mode != None:
        _align = mode
    return _align

_text_cache = {}
def text(str, x, y, width=None, draw=True, cached=True, **kwargs):
    fill, stroke = color_mixin(**kwargs)
    if fill is None:
        fill = Color(0)
    fontname   = kwargs.get("font", _fontname)
    fontsize   = kwargs.get("fontsize", _fontsize)
    lineheight = kwargs.get("lineheight", _lineheight)
    align      = kwargs.get("align", _align)
    id = (str, fontname, fontsize)
    if id in _text_cache:
        txt = _text_cache[id]
    else:
        txt = pyglet_font.Text(font(fontname, fontsize), str, color=list(fill))
        if cached:
            # Caching is meant for text labels, we shouldn't cache entire pages.
            _text_cache[id] = txt
    txt.width = width
    txt.halign = align
    txt.line_height = lineheight*fontsize
    if draw:
        push()
        translate(x, y)
        txt.draw()
        pop()
    return txt
    
def textwidth(txt):
    if not isinstance(txt, pyglet_font.Text):
        txt = text(txt, x, y, draw=False)
    return txt.width

def textheight(txt, width=None):
    if not isinstance(txt, pyglet_font.Text):
        txt = text(txt, x, y, width=width, draw=False)
    return txt.height

def textmetrics(txt):
    if not isinstance(txt, pyglet_font.Text):
        txt = text(txt, x, y, width=width, draw=False)
    return (txt.width, txt.height)

def textpath(str, x, y):
    raise NotImplementedError

#=====================================================================================================

#--- UTILITIES ----------------------------------------------------------------------------------------

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
    if v2 == None:
        v1, v2 = 0, v1
    if bias == None:
        r = rnd()
    else:
        r = rnd()**_rnd_exp(bias)
    x = r * (v2-v1) + v1
    if isinstance(v1, int) and isinstance(v2, int):
        x = int(x)
    return x

def grid(cols, rows, colwidth=1, rowheight=1, shuffled=False):
    rows = range(int(rows))
    cols = range(int(cols))
    if shuffled:
        shuffle(rows)
        shuffle(cols)
    for y in rows:
        for x in cols:
            yield (x*colwidth, y*rowheight)

def files(path="*"):
    return glob(path)

#=====================================================================================================

#--- TRANSITION --------------------------------------------------------------------------------------
# Transition.update() will tween from the last value to transition.set() new value in the given time.
# Transitions are used as attributes (e.g. position, rotation) for the Layer class.

TIME = 0 # the current time in this frame changes when the canvas is updated
    
LINEAR = "linear"
SMOOTH = "smooth"
_KAPPA = 0.5522847498

class Transition(object):

    def __init__(self, value, interpolation=SMOOTH):
        self._v0 = value # original value
        self._vi = value # current value
        self._v1 = value # desired value
        self._t0 = TIME  # start time
        self._t1 = TIME  # end time
        self._interpolation = interpolation
        self._d = 0
    
    def copy(self):
        t = Transition(None)
        t._v0 = self._v0
        t._vi = self._vi
        t._v1 = self._v1
        t._t0 = self._t0
        t._t1 = self._t1
        t._interpolation = self._interpolation
        t._d = self._d
        return t
    
    def get(self):
        return self._v1 # desired value
    def set(self, value, duration=1.0):
        self._v1 = value
        self._v0 = self._vi
        self._t0 = TIME # now
        self._t1 = TIME + duration
        self._d = (self._t1 - self._t0) * _KAPPA
    value = property(get, set)

    @property 
    def current(self): 
        return self._vi
    now = current
    
    @property
    def previous(self):
        return self._v0
    
    @property
    def done(self):
        return TIME >= self._t1
    
    def update(self):
        """ Calculates the new current value.
        The transition approaches the desired value according to the interpolation:
        - LINEAR: even transition over the given duration time,
        - SMOOTH: transition goes slower at the end.
        """
        if TIME >= self._t1:
            self._vi = self._v1
        else:
            # Calculate t, the elapsed time as a number between 0.0 and 1.0.
            t = (TIME - self._t0) / (self._t1 - self._t0)
            if self._interpolation == LINEAR:
                xx, self._vi = bezier.linepoint(t, self._t0, self._v0, self._t1, self._v1)
            else:
                x, self._vi, xx, xxx, xxxx, xxxxx = bezier.curvepoint(t, \
                    self._t0, 
                    self._v0, \
                    self._t0 + self._d, 
                    self._v0, \
                    self._t1 - self._d, 
                    self._v1, \
                    self._t1, 
                    self._v1)

#--- LAYER -------------------------------------------------------------------------------------------
# The Layer class is responsible for the following:
# - it has a draw() method to patch, all sorts of NodeBox drawing commands can be put here,
# - it has a transformation origin point and rotates/scales its drawn items as a group,
# - it has child layers that transform relative to this layer,
# - when its attributes (position, scale, angle, ...) change, they will tween smoothly over time. 

class Layer(list):

    def __init__(self, x=0, y=0, width=None, height=None, origin=(0.5,0.5), scale=1.0, rotation=0, opacity=1.0, duration=1.0, parent=None):
        self.parent    = None
        self._x        = Transition(x)
        self._y        = Transition(y)
        self._width    = Transition(width)
        self._height   = Transition(height)
        self._dx       = Transition(origin[0])
        self._dy       = Transition(origin[1])
        self._scale    = Transition(scale)
        self._rotation = Transition(rotation)
        self._opacity  = Transition(opacity, interpolation=LINEAR)
        self.duration  = duration
        self.top       = True # draw on top of or beneath parent?
        self.flipped   = False
        self.hidden    = False
        self.name      = None
    
    def append(self, layer):
        list.append(self, layer)
        layer.parent = self
        
    def _get_x(self):
        return self._x.get()
    def _get_y(self):
        return self._y.get()
    def _get_width(self):
        return self._width.get()
    def _get_height(self):
        return self._height.get()
    def _get_origin(self):
        return (self._dx, self._dy)
    def _get_scale(self): 
        return self._scale.get()
    def _get_rotation(self): 
        return self._rotation.get()
    def _get_opacity(self): 
        return self._opacity.get()

    def _set_x(self, x):
        self._x.set(x, self.duration)
    def _set_y(self, y):
        self._y.set(y, self.duration)
    def _set_width(self, width):
        self._width.set(width, self.duration)
    def _set_height(self, height):
        self._height.set(height, self.duration)
    def _set_origin(self, xy):
        assert len(xy) == 2, "_set_origin requires a tuple with two floats"
        self._dx.set(xy[0], self.duration)
        self._dy.set(xy[1], self.duration)
    def _set_scale(self, scale): 
        self._scale.set(scale, self.duration)
    def _set_rotation(self, rotation):
        self._rotation.set(rotation, self.duration)
    def _set_opacity(self, opacity):
        self._opacity.set(opacity, self.duration)

    x        = property(_get_x, _set_x)
    y        = property(_get_y, _set_y)
    width    = property(_get_width, _set_width)
    height   = property(_get_height, _set_height)
    origin   = property(_get_origin, _set_origin)
    scale    = property(_get_scale, _set_scale)
    rotation = property(_get_rotation, _set_rotation)
    opacity  = property(_get_opacity, _set_opacity)
    
    @property
    def abs_x(self):
        if self.parent == None:
            return self.x
        return self.x + self.parent.abs_x

    @property
    def abs_y(self):
        if self.parent == None:
            return self.y
        return self.y + self.parent.abs_y

    # Origin as a number between  0.0-1.0, based on the layer's width and height.
    def _get_relative_origin(self):
        return self._dx.get() * self._width.get(), self._dy.get() * self._height.get()
    def _set_relative_origin(self, xy):
        self._dx.set(xy[0] * self._width.get())
        self._dy.set(xy[1] * self._height.get())
    relative_origin = property(_get_relative_origin, _set_relative_origin)
    
    def _update(self):
        """ Called each frame from canvas.update() to update the layer transitions.
        """
        self._x.update()
        self._y.update()
        self._width.update()
        self._height.update()
        self._dx.update()
        self._dy.update()
        self._scale.update()
        self._rotation.update()
        self._opacity.update()
        # Allow overriding code to do custom updating.
        self.update()
        # Update child layers
        for layer in self:
            layer._update()
            
    def update(self):
        """Override this method to provide custom updating code."""
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
        
        # Calculate the origin point
        ox = self._dx.current * self._width.current
        oy = self._dy.current * self._height.current
        
        # Center the contents around the origin point
        glTranslatef(ox, oy, 0)
        glTranslatef(self._x.current, self._y.current, 0)
        glRotatef(self._rotation.current, 0, 0, 1)
        # TODO: Fixed flipped layers
        #if self.flipped:
        #    glScalef(-1, 1, 1)
        glScalef(self._scale.current, self._scale.current, 1)
        # Translate back to the current point
        glTranslatef(-ox, -oy, 0)
        for layer in filter(lambda x: not x.top, self):
            layer._draw()
        # Actually draw the contents of the layer.
        # This method is normally subclassed.
        self.draw()
        for layer in filter(lambda x: x.top, self):
            layer._draw()
        glPopMatrix()
        
    def draw(self):
        """Override this method to provide custom drawing code for this layer.
        
        At this point, the layer is already transformed correctly."""
        
    def layer_at(self, x, y):
        if not self.hit_test(x, y): return None
        for layer in self:
            child_layer = layer.layer_at(x, y)
            if child_layer is not None:
                return child_layer
        else:
            return self

    def hit_test(self, x, y):
        return (0 <= x - self.x <= self.width and
                0 <= y - self.y <= self.height)
                
    #### Events ####
    
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers): pass
    def on_mouse_enter(self, x, y): pass
    def on_mouse_leave(self, x, y): pass
    def on_mouse_motion(self, x, y, dx, dy): pass
    def on_mouse_press(self, x, y, button, modifiers): pass
    def on_mouse_release(self, x, y, button, modifiers): pass
    def on_mouse_scroll(self, x, y, scroll_x, scroll_y): pass
        
    #### Binding ####

    def bind(self, function):
        """Creates a Layer method from the given function. 
        The function is expected to take Layer (i.e. self) as first parameter.
        Layer.draw() can be implemented by inheriting the class or by patching the method:
        class MyDraw:
            def draw(self):
                ...
        OR
        def draw(layer):
            ...
        layer = Layer()
        layer.bind(draw)
        """
        setattr(self, function.__name__, instancemethod(function, self))

    #### Copy ####

    def copy(self, parent=None):
        l = layer()
        l.parent = parent
        for attr in ["_x", "_y", "_dx", "_dy", "_scale", "_rotation", "_opacity", "draw", "top", "flipped", "hidden"]:
            setattr(l, attr, getattr(self, attr).copy())
        for layer in self:
            l.append(layer.copy(parent=l))
        return l
        
    def __repr__(self):
        if self.name is not None:
            name_repr = "name=%s, " % self.name
        else:
            name_repr = ""
        return "Layer(%sx=%.2f, y=%.2f, scale=%.2f, angle=%.2f, opacity=%.2f, duration=%.2f)" % \
            (name_repr, self.x, self.y, self.scale, self.rotation, self.opacity, self.duration)

#=====================================================================================================

#--- INPUT -------------------------------------------------------------------------------------------

# Mouse cursors
DEFAULT = "default"
CROSS   = pyglet_window.Window.CURSOR_CROSSHAIR
HAND    = pyglet_window.Window.CURSOR_HAND
HIDDEN  = pyglet_window.Window.CURSOR_NO
TEXT    = pyglet_window.Window.CURSOR_TEXT
WAIT    = pyglet_window.Window.CURSOR_WAIT

# Mouse buttons
MOUSE_LEFT   = pyglet.window.mouse.LEFT
MOUSE_MIDDLE = pyglet.window.mouse.MIDDLE
MOUSE_RIGHT  = pyglet.window.mouse.RIGHT

# Keys
from pyglet.window import key as KEYCODE
KEY_BACKSPACE = "backspace"
KEY_TAB       = "tab"
KEY_RETURN    = "return"
KEY_SPACE     = "space"
KEY_ESC       = "escape"
KEY_CTRL      = "ctrl"
KEY_LCTRL     = "lctrl"
KEY_RCTRL     = "rctrl"
KEY_SHIFT     = "shift"
KEY_LSHIFT    = "lshift"
KEY_RSHIFT    = "rshift"
KEY_UP        = "up"
KEY_DOWN      = "down"
KEY_LEFT      = "left"
KEY_RIGHT     = "right"

# Modifiers - in key_pressed(), check for: modifiers & SHIFT
SHIFT   = KEYCODE.MOD_SHIFT
CTRL    = KEYCODE.MOD_CTRL
OPTION  = ALT = KEYCODE.MOD_OPTION
COMMAND = KEYCODE.MOD_COMMAND

# Somebody needs to expand this list.
characters = {
    "backslash" : "\\",
    "comma"     : ",",
    "equal"     : "+",
    "minus"     : "-",
    "period"    : ".",
    "semicolon" : ";",
    "slash"     : "/",
    "quoteleft" : "`",
}
def key(code):
    """ Returns a character from a Pyglet symbol string from a key code.
    For example: 45 => KEY_MINUS => "-".
    """
    k = pyglet_window.key.symbol_string(code).lower()
    k = k.lstrip("_")
    k = characters.get(k, k) 
    return k

#--- CANVAS ------------------------------------------------------------------------------------------
# The Canvas class is responsible for the following:
# - it is a collection of drawable Layer objects AND it has its own draw() method to patch,
# - it opens the application window,
# - it handles keyboard and mouse interaction,
# - it keeps track of time and has a frames-per-second rate,
# - it can return the current frame as a texture,
# - it can save the current frame as an image.
# Setting the name property also sets the caption for the window.

VERY_LIGHT_GREY = 0.95

class Canvas(list):

    def __init__(self, config=None):
        self._window = pyglet_window.Window(visible=False, config=config)
        self._window.on_mouse_drag = self._on_mouse_drag
        self._window.on_mouse_enter = self._on_mouse_enter
        self._window.on_mouse_leave = self._on_mouse_leave
        self._window.on_mouse_motion = self._on_mouse_motion
        self._window.on_mouse_press = self._on_mouse_press
        self._window.on_mouse_release = self._on_mouse_release
        self._window.on_mouse_scroll = self._on_mouse_scroll
        self._window.on_close        = self._stop
        self.fps     = None # frames per second
        self._frame  = 0    # current frame
        self._t      = 0    # last frame time
        self._mouse  = Point(0,0)
        self._cursor = DEFAULT
        self._runs   = False
        self._buffer = None
        self._current_layer = None
        self._dragging_layer = None
        self._entered_layers = []
        
    def setup(self):
        pass
        
    def update(self):
        pass
        
    def draw(self):
        self.clear()
        
    def stop(self):
        pass

    def _get_name(self):
        return self._window.caption
    def _set_name(self, str):
        self._window.set_caption(str)
    name = property(_get_name, _set_name)

    def append(self, layer):
        list.append(self, layer)
             
    def _get_width(self):
        return self._window.width
    def _get_height(self):
        return self._window.height
    def _get_size(self):
        return (self.width, self.height)
    def _set_width(self, v):
        global WIDTH
        self._window.width = WIDTH = v
    def _set_height(self, v):
        global HEIGHT
        self._window.height = HEIGHT = v
    def _set_size(self, width, height):
        self.width  = width
        self.height = height
    
    width  = property(_get_width, _set_width)
    height = property(_get_height, _set_height)
    size   = property(_get_size, _set_size)

    def _get_fullscreen(self):
        return self._window.fullscreen
    def _set_fullscreen(self, mode=True):
        self._window.set_fullscreen(mode)
    fullscreen = property(_get_fullscreen, _set_fullscreen)

    @property
    def frame(self):
        """ Returns the current frame number.
        """
        return self._frame

    @property
    def mouse(self):
        """ Returns an (x, y)-tuple with the mouse position on screen.
        """
        return self._mouse

    def _set_cursor(self, mode):
        self._cursor = mode
        self._window.set_mouse_cursor(self._window.get_system_mouse_cursor(mode))
    def _get_cursor(self):
        return self._cursor
    cursor = property(_get_cursor, _set_cursor)
    
    def layer_at(self, x, y):
        """Find a layer at the specified coordinates.
        
        This method returns None if no layer was found."""
        for layer in self:
            l = layer.layer_at(x, y)
            if l is not None:
                return l
        return None
        
    #### Events ####
    
    def _on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.on_mouse_drag(x, y, dx, dy, buttons, modifiers)
        if self._dragging_layer is None: return
        self._dragging_layer.on_mouse_drag(x, y, dx, dy, buttons, modifiers)
        
    def _on_mouse_enter(self, x, y):
        self.on_mouse_enter(x, y)
        layer = self.layer_at(x, y)
        if layer is None: return
        layer.on_mouse_enter(x, y)
        
    def _on_mouse_leave(self, x, y):
        self.on_mouse_leave(x, y)
        layer = self.layer_at(x, y)
        if layer is None: return
        layer.on_mouse_leave(x, y)
        
    def _on_mouse_motion(self, x, y, dx, dy):
        self._mouse.x, self._mouse.y = x, y
        self.on_mouse_motion(x, y, dx, dy)
        # Check if the existing entered layers are still entered.
        layers_to_remove = []
        for l in self._entered_layers:
            if not l.hit_test(x, y):
                layers_to_remove.append(l)
        # Remove all marked layers
        for l in layers_to_remove:
            l.on_mouse_leave(x, y)
            self._entered_layers.remove(l)
        # Get the deepest nested layer. All layers in the hierarchy, up to the root,
        # will receive the on_mouse_enter event.
        current_layer = deepest_layer = self.layer_at(x, y)
        if current_layer is None: return
        while current_layer is not None:
            if current_layer not in self._entered_layers:
                self._entered_layers.append(current_layer)
                current_layer.on_mouse_enter(x, y)
            current_layer = current_layer.parent
        # Only the deepest nested layer will receive the mouse motion event.
        deepest_layer.on_mouse_motion(x, y, dx, dy)
    
    def _on_mouse_press(self, x, y, button, modifiers):
        self.on_mouse_press(x, y, button, modifiers)
        layer = self.layer_at(x, y)
        if layer is None: return
        self._dragging_layer = layer
        layer.on_mouse_press(x, y, button, modifiers)
        
    def _on_mouse_release(self, x, y, button, modifiers):
        self._dragging_layer = None
        self.on_mouse_release(x, y, button, modifiers)
        layer = self.layer_at(x, y)
        if layer is None: return
        layer.on_mouse_release(x, y, button, modifiers)
        
    def _on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.on_mouse_scroll(x, y, scroll_x, scroll_y)
        layer = self.layer_at(x, y)
        if layer is None: return
        layer.on_mouse_scroll(x, y, scroll_x, scroll_y)

    # These methods are meant to be overridden
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers): pass
    def on_mouse_enter(self, x, y): pass
    def on_mouse_leave(self, x, y): pass
    def on_mouse_motion(self, x, y, dx, dy): pass
    def on_mouse_press(self, x, y, button, modifiers): pass
    def on_mouse_release(self, x, y, button, modifiers): pass
    def on_mouse_scroll(self, x, y, scroll_x, scroll_y): pass

    def _setup(self):
        # Set the window color, this will be transparent in saved images:
        glClearColor(VERY_LIGHT_GREY, VERY_LIGHT_GREY, VERY_LIGHT_GREY, 0)
        glLoadIdentity()
        # Enable alpha transparency:
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.clear()
        self.anti_aliasing()
        self._window.dispatch_events()
        self._window.set_visible()
        self.setup()
        self._runs = True

    def _draw(self):

        """Draws the canvas and the underlying layers.
        
        This method should give the same result each time it gets drawn;
        only _update should advance state.
        """

        # Draw my own contents
        glPushMatrix()
        self.draw()
        glPopMatrix()
        
        # Draw the layers
        glPushMatrix()
        for layer in self:
            layer._update()
            layer._draw()
        glPopMatrix()
        self._window.flip()

    def _update(self):

        """Updates the canvas and the underlying layers.
        
        This method does not actually draw anything, it only update state.
        """

        if not self._runs:
            self._setup()
        global TIME
        TIME = time()
        if self.fps == None or TIME-self._t > 1.0/self.fps:
            self._window.dispatch_events()
            self._frame += 1
            self._t = TIME
            # Update the canvas
            self.update()
            # Update the layers
            for layer in self:
                layer._update()

    def clear(self):
        """ Clears the previous frame from the canvas.
        """
        glClear(GL_COLOR_BUFFER_BIT)
    
    def _stop(self):
        self.stop()
        self._window.close()
        exit(0)
    
    def run(self):
        while not self.done:
            self._update()
            self._draw()

    def _get_done(self):
        return self._window.has_exit
    def _set_done(self, done=False):
        # Do canvas.done = True to close the drawing window.
        if done:
            self._stop()
    done = property(_get_done, _set_done)

    def screenshot(self, crop=(0,0,0,0)):
        """ Returns a screenshot of the current frame as a texture.
        This texture can be passed to image().
        """
        w = ceil2(self._window.width)
        h = ceil2(self._window.height)
        if not self._buffer \
        or self._buffer.width  < w \
        or self._buffer.height < h:
            self._buffer = pyglet_image.Texture.create(w, h)
        glBindTexture(GL_TEXTURE_2D, self._buffer.id)
        glCopyTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 0, 0, w, h, 0)
        return self._buffer.get_region(
            crop[0], 
            crop[1], 
            self._window.width  - crop[0] - crop[2], 
            self._window.height - crop[1]  -crop[3]
        )
        
    buffer = screenshot

    def save(self, path):
        """ Saves the current frame as a PNG-file.
        """
        pyglet_image.get_buffer_manager().get_color_buffer().save(path)

    def anti_aliasing(self, mode=True):
        if mode == True:
            glEnable(GL_LINE_SMOOTH)
            #glEnable(GL_POLYGON_SMOOTH)
        else:
            glDisable(GL_LINE_SMOOTH)
            #glDisable(GL_POLYGON_SMOOTH)

    def bind(self, function):
        setattr(self, function.__name__, instancemethod(function, self))

#--- LIBRARIES ---------------------------------------------------------------------------------------
# Import the library and assign it a _ctx variable containing the current context.
# This mimics the behavior in NodeBox.

def ximport(library):
    from sys import modules
    library = __import__(library)
    library._ctx = modules[__name__]
    return library

#-----------------------------------------------------------------------------------------------------
# Linear interpolation math for BezierPath.point() etc.

import bezier

#-----------------------------------------------------------------------------------------------------
# Expose the canvas and some common canvas properties on global level.
# Some magic constants from NodeBox are commands here:
# - WIDTH  => width()
# - HEIGHT => height()
# - FRAME  => frame()
# - MOUSEX, MOUSEY => mouse()

canvas = Canvas()

def run():
    canvas.run()

def size(width=None, height=None):
    if width != None:
        canvas._window.width = width
    if height != None:
        canvas._window.height = height
    return canvas.size

def width():
    return canvas._window.width
WIDTH = width()

def height():
    return canvas._window.height
HEIGHT = height()

def fullscreen(mode=None):
    if mode != None:
        canvas.fullscreen = mode
    return canvas.fullscreen

def speed(fps=None):
    if fps != None:
        canvas.fps = fps
    return canvas.fps

def frame():
    return canvas.frame
    
def screenshot(crop=(0,0,0,0)):
    return canvas.screenshot(crop)

buffer = screenshot

def mouse():
    return (canvas.mouse.x, canvas,mouse.y)
    
def cursor(mode=None):
    """ Sets the current mouse cursor (DEFAULT, CROSS, HAND, HIDDEN, TEXT or WAIT).
    """
    if mode != None:
        canvas.cursor = mode
    return canvas.cursor

def nocursor():
    """ Hides the mouse cursor.
    """
    canvas.cursor = HIDDEN

#-----------------------------------------------------------------------------------------------------
# Performance statistics.
# Psyco should be off.

def profile_run(n):
    for i in range(n):
        canvas.update()

def profile(frames=200, top=30):
    import cProfile
    import pstats
    from os import remove
    #cProfile.run("profile_run("+str(frames)+")", "_profile")
    cProfile.run("for i in range("+str(frames)+"): canvas.update()", "_profile")
    p = pstats.Stats("_profile")
    p.sort_stats("cumulative").print_stats(top)
    remove("_profile")