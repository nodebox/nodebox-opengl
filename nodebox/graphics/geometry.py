#=== SHADER ==========================================================================================
# 2D geometry functions.
# Authors: Tom De Smedt
# License: BSD (see LICENSE.txt for details).
# Copyright (c) 2008 City In A Bottle (cityinabottle.org)
# http://cityinabottle.org/nodebox

from math import sqrt, pow
from math import sin, cos, atan2, degrees, radians, pi

INFINITE = 1e15 # float("inf") doesn't work on windows.

#=====================================================================================================

#--- ROTATION ----------------------------------------------------------------------------------------

def angle(x0, y0, x1, y1):
    """ Returns the angle between two points.
    """
    return degrees(atan2(y1-y0, x1-x0))

def distance(x0, y0, x1, y1):
    """ Returns the distance between two points.
    """
    return sqrt(pow(x1-x0, 2) + pow(y1-y0, 2))

def coordinates(x0, y0, distance, angle):
    """ Returns the location of a point by rotating around origin (x0,y0).
    """
    return (x0 + cos(radians(angle)) * distance,
            y0 + sin(radians(angle)) * distance)

def rotate(x, y, x0, y0, angle):
    """ Returns the coordinates of (x,y) rotated around origin (x0,y0).
    """
    x, y = x-x0, y-y0
    a, b = cos(radians(angle)), sin(radians(angle))
    return (x*a-y*b+x0, y*a+x*b+y0)

def reflect(x, y, x0, y0, d=1.0, a=180):
    """ Returns the reflection of a point through origin (x0,y0).
    """
    return coordinates(x0, y0, d*distance(x0,y0,x,y), a+angle(x0,y0,x,y))
    
# Fast C implementations:
try: from nodebox.ext.geometry import angle, distance, coordinates, rotate
except:
    pass

#--- INTERPOLATION -----------------------------------------------------------------------------------
    
def lerp(a, b, t):
    """ Returns the linear interpolation between a and b for time t between 0.0-1.0.
        For example: lerp(100, 200, 0.5) => 150.
    """
    if t < 0.0: return a
    if t > 1.0: return b
    return a + (b-a)*t
    
def smoothstep(a, b, x):
    """ Returns a smooth transition between 0.0 and 1.0 using Hermite interpolation (cubic spline),
        where x is a number between a and b. The return value will ease (slow down) as x nears a or b.
        For x smaller than a, returns 0.0. For x bigger than b, returns 1.0.
    """
    if x < a: return 0.0
    if x >=b: return 1.0
    x = float(x-a) / (b-a)
    return x*x * (3-2*x)

def bounce(x):
    """ Returns a bouncing value between 0.0 and 1.0 (e.g. Mac OS X Dock) for a value between 0.0-1.0.
    """
    return abs(sin(2*pi * (x+1) * (x+1)) * (1-x))

def clamp(v, a, b):
    return max(a, min(v, b))
    
# Fast C implementations:
try: from nodebox.ext.geometry import smoothstep
except:
    pass

#--- INTERSECTION ------------------------------------------------------------------------------------

def line_line_intersection(x1, y1, x2, y2, x3, y3, x4, y4, infinite=False):
    """ Determines the intersection point of two lines, or two finite line segments if infinite=False.
        When the lines do not intersect, returns an empty list.
    """
    # Based on: P. Bourke, http://local.wasp.uwa.edu.au/~pbourke/geometry/lineline2d/
    ua = (x4-x3)*(y1-y3) - (y4-y3)*(x1-x3)
    ub = (x2-x1)*(y1-y3) - (y2-y1)*(x1-x3)
    d  = (y4-y3)*(x2-x1) - (x4-x3)*(y2-y1)
    if d == 0:
        if ua == ub == 0:
            # The lines are coincident
            return []
        else:
            # The lines are parallel.
            return []
    ua /= float(d)
    ub /= float(d)
    if not infinite and not (0<=ua<=1 and 0<=ub<=1):
        # Intersection point is not within both line segments.
        return None, None
    return [(x1+ua*(x2-x1), y1+ua*(y2-y1))]
    
def circle_line_intersection(cx, cy, radius, x1, y1, x2, y2, infinite=False):
    """ Returns a list of points where the circle and the line intersect.
        Returns an empty list when the circle and the line do not intersect.
    """	
    # Based on: http://www.vb-helper.com/howto_net_line_circle_intersections.html
    dx = x2-x1
    dy = y2-y1
    A = dx*dx + dy*dy
    B = 2 * (dx*(x1-cx) + dy*(y1-cy))
    C = pow(x1-cx, 2) + pow(y1-cy, 2) - radius*radius
    det = B*B - 4*A*C
    if A <= 0.0000001 or det < 0: 
        return []
    elif det == 0:
        # One point of intersection.
        t = -B / (2*A)
        return [(x1+t*dx, y1+t*dy)]
    else:
        # Two points of intersection.
        # A point of intersection lies on the line segment if 0 <= t <= 1,
        # and on an extension of the segment otherwise.
        points = []
        det2 = sqrt(det)
        t1 = (-B+det2) / (2*A)
        t2 = (-B-det2) / (2*A)
        if infinite or 0 <= t1 <= 1: points.append((x1+t1*dx, y1+t1*dy))  
        if infinite or 0 <= t2 <= 1: points.append((x1+t2*dx, y1+t2*dy))
        return points

def intersection(*args, **kwargs):
    if len(args) == 8:
        return line_line_intersection(*args, **kwargs)
    if len(args) == 7:
        return circle_line_intersection(*args, **kwargs)

def point_in_polygon(points, x, y):
    """ Ray casting algorithm.
        Determines how many times a horizontal ray starting from the point 
        intersects with the sides of the polygon. 
        If it is an even number of times, the point is outside, if odd, inside.
        The algorithm does not always report correctly when the point is very close to the boundary.
        The polygon is passed as a list of (x,y)-tuples.
    """
    odd = False
    n = len(points)
    for i in range(n):
        j = i<n-1 and i+1 or 0
        x0, y0 = points[i][0], points[i][1]
        x1, y1 = points[j][0], points[j][1]
        if (y0 < y and y1 >= y) or (y1 < y and y0 >= y):
            if x0 + (y-y0) / (y1-y0) * (x1-x0) < x:
                odd = not odd
    return odd

#=====================================================================================================

#--- AFFINE TRANSFORM --------------------------------------------------------------------------------

def superformula(m, n1, n2, n3, phi):
    """ A generalization of the superellipse first proposed by Johan Gielis.
        It can be used to describe many complex shapes and curves that are found in nature.
    """
    if n1 == 0: 
        return (0,0)
    a = 1.0
    b = 1.0
    r = pow(pow(abs(cos(m * phi/4) / a), n2) + \
            pow(abs(sin(m * phi/4) / b), n3), 1/n1)
    if abs(r) == 0:
        return (0,0)
    r = 1 / r
    return (r*cos(phi), r*sin(phi))

# Fast C implementation:
try: from nodebox.ext.geometry import superformula
except:
    pass

#=====================================================================================================

#--- AFFINE TRANSFORM --------------------------------------------------------------------------------
# Based on http://www.senocular.com/flash/tutorials/transformmatrix/

class AffineTransform:
    
    def __init__(self, transform=None):
        """ A geometric transformation in Euclidean space (i.e. 2D)
            that preserves collinearity and ratio of distance between points.
            Linear transformations include rotation, translation, scaling, shear.
        """
        if isinstance(transform, AffineTransform):
            self.matrix = list(transform.matrix)
        else:
            self.matrix = self.identity
            
    def copy(self):
        return AffineTransform(self)

    def prepend(self, transform):
        self.matrix = self._mmult(self.matrix, transform.matrix)        
    def append(self, transform):
        self.matrix = self._mmult(transform.matrix, self.matrix)
        
    concat = append

    def _mmult(self, a, b):
        """ Returns the 3x3 matrix multiplication of A and B.
            Note that scale(), translate(), rotate() work with premultiplication,
            e.g. the matrix A followed by B = BA and not AB.
        """
        # No need to optimize (C version is just as fast).
        return [
            a[0]*b[0] + a[1]*b[3], 
            a[0]*b[1] + a[1]*b[4], 
            0,
            a[3]*b[0] + a[4]*b[3], 
            a[3]*b[1] + a[4]*b[4], 
            0,
            a[6]*b[0] + a[7]*b[3] + b[6], 
            a[6]*b[1] + a[7]*b[4] + b[7], 
            1
        ]
              
    def invert(self):
        """ Multiplying a matrix by its inverse produces the identity matrix.
        """
        m = self.matrix
        d = m[0]*m[4] - m[1]*m[3]
        self.matrix = [
             m[4]/d, -m[1]/d, 0,
            -m[3]/d,  m[0]/d, 0,
             (m[3]*m[7]-m[4]*m[6])/d,
            -(m[0]*m[7]-m[1]*m[6])/d, 
             1
        ]
    
    @property
    def inverse(self):
        m = self.copy(); m.invert(); return m;

    @property
    def identity(self):
        return [1,0,0, 0,1,0, 0,0,1]
        
    @property
    def rotation(self):
        return (degrees(atan2(self.matrix[1], self.matrix[0])) + 360) % 360 # 0.0 => 360.0
        
    def scale(self, x, y=None):
        if y==None: y = x
        self.matrix = self._mmult([x,0,0, 0,y,0, 0,0,1], self.matrix)
    
    def translate(self, x, y):
        self.matrix = self._mmult([1,0,0, 0,1,0, x,y,1], self.matrix)
    
    def rotate(self, degrees=0, radians=0):
        radians = degrees and degrees*pi/180 or radians
        c = cos(radians)
        s = sin(radians)
        self.matrix = self._mmult([c,s,0, -s,c,0, 0,0,1], self.matrix)
    
    def transform_point(self, x, y):
        """ Returns the new coordinates of (x,y) after transformation.
        """
        m = self.matrix
        return (x*m[0]+y*m[3]+m[6], x*m[1]+y*m[4]+m[7])
        
    apply = transform_point
    
    def transform_path(self, path):
        """ Returns a BezierPath object with the transformation applied.
        """
        p = path.__class__() # Create a new BezierPath.
        for pt in path:
            if pt.cmd == "close":
                p.closepath()
            elif pt.cmd == "moveto":
                p.moveto(*self.apply(pt.x, pt.y))
            elif pt.cmd == "lineto":
                p.lineto(*self.apply(pt.x, pt.y))
            elif pt.cmd == "curveto":
                vx1, vy1 = self.apply(pt.ctrl1.x, pt.ctrl1.y)
                vx2, vy2 = self.apply(pt.ctrl2.x, pt.ctrl2.y)
                x, y = self.apply(pt.x, pt.y)
                p.curveto(vx1, vy1, vx2, vy2, x, y)
        return p
    
    # Compatibility with NodeBox.
    transformPoint = transform_point
    transformBezierPath = transform_path
    
    def map(self, points):
        return [self.apply(*pt) for pt in points]

Transform = AffineTransform

#=====================================================================================================

#--- POINT -------------------------------------------------------------------------------------------

class Point(object):
    
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def _get_xy(self):
        return (self.x, self.y)
    def _set_xy(self, (x,y)):
        self.x = x
        self.y = y
        
    xy = property(_get_xy, _set_xy)

    def __iter__(self):
        return iter((self.x, self.y))

    def __repr__(self):
        return "Point(x=%.1f, y=%.1f)" % (self.x, self.y)
        
    def __eq__(self, pt):
        if not isinstance(pt, Point): return False
        return self.x == pt.x \
           and self.y == pt.y
    
    def __ne__(self, pt):
        return not self.__eq__(pt)

#--- BOUNDS ------------------------------------------------------------------------------------------

class Bounds:
    
    def __init__(self, x, y, width, height):
        """ Creates a bounding box.
            The bounding box is an untransformed rectangle that encompasses a shape or group of shapes.
        """
        # context.Layer does not always have a width or height defined (i.e. infinite layer):
        if width == None: width = INFINITE
        if height == None: height = INFINITE
        # Normalize if width or height is negative:
        if width < 0: x, width = x+width,  -width
        if height < 0: y, height = y+height, -height
        self.x = x
        self.y = y
        self.width = width 
        self.height = height
    
    def copy(self):
        return Bounds(self.x, self.y, self.width, self.height)
    
    def __iter__(self):
        """ You can conveniently unpack bounds: x,y,w,h = Bounds(0,0,100,100)
        """
        return iter((self.x, self.y, self.width, self.height))

    def intersects(self, b):
        """ Return True if a part of the two bounds overlaps.
        """
        return max(self.x, b.x) < min(self.x+self.width, b.x+b.width) \
           and max(self.y, b.y) < min(self.y+self.height, b.y+b.height)
    
    def intersection(self, b):
        """ Returns bounds that encompass the intersection of the two.
            If there is no overlap between the two, None is returned.
        """
        if not self.intersects(b): 
            return None
        mx, my = max(self.x, b.x), max(self.y, b.y)
        return Bounds(mx, my, 
            min(self.x+self.width, b.x+b.width) - mx, 
            min(self.y+self.height, b.y+b.height) - my)
    
    def union(self, b):
        """ Returns bounds that encompass the union of the two.
        """
        mx, my = min(self.x, b.x), min(self.y, b.y)
        return Bounds(mx, my, 
            max(self.x+self.width, b.x+b.width) - mx, 
            max(self.y+self.height, b.y+b.height) - my)

    def contains(self, *a):
        """ Returns True if the given point or rectangle falls within the bounds.
        """
        if len(a) == 2: a = [Point(a[0], a[1])]
        if len(a) == 1:
            a = a[0]
            if isinstance(a, Point):
                return a.x >= self.x and a.x <= self.x+self.width \
                   and a.y >= self.y and a.y <= self.y+self.height
            if isinstance(a, Bounds):
                return a.x >= self.x and a.x+a.width <= self.x+self.width \
                   and a.y >= self.y and a.y+a.height <= self.y+self.height
            
    def __eq__(self, b):
        if not isinstance(b, Bounds): 
            return False
        return self.x == b.x \
           and self.y == b.y \
           and self.width == b.width \
           and self.height == b.height
    
    def __ne__(self, b):
        return not self.__eq__(b)
    
    def __repr__(self):
        return "Bounds(%.1f, %.1f, %.1f, %.1f)" % (self.x, self.y, self.width, self.height)

#=====================================================================================================

#--- TESSELLATION ------------------------------------------------------------------------------------
# OpenGL can only display simple convex polygons directly.
# A polygon is simple if the edges intersect only at vertices, there are no duplicate vertices, 
# and exactly two edges meet at any vertex. 
# Polygons containing holes or polygons with intersecting edges must first be subdivided 
# into simple convex polygons before they can be displayed.
# Such subdivision is called tessellation.

# Algorithm adopted from Squirtle:
#
#  Copyright (c) 2008 Martin O'Leary. 
#
#  All rights reserved.  
#
#  Redistribution and use in source and binary forms, with or without modification, 
#  are permitted provided that the following conditions are met:   
#  * Redistributions of source code must retain the above copyright notice, 
#    this list of conditions and the following disclaimer. 
#  * Redistributions in binary form must reproduce the above copyright notice, 
#    this list of conditions and the following disclaimer in the documentation 
#    and/or other materials provided with the distribution. 
#  * Neither the name(s) of the copyright holders nor the names of its contributors may be used to 
#    endorse or promote products derived from this software without specific prior written permission.  
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
#  INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A 
#  PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY DIRECT, 
#  INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
#  PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) 
#  HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT 
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
#  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from sys import platform
from ctypes import CFUNCTYPE, POINTER, byref, cast
from ctypes import CFUNCTYPE as _CFUNCTYPE
from pyglet.gl import \
    GLdouble, GLvoid, GLenum, GLfloat, pointer, \
    gluNewTess, gluTessProperty, gluTessNormal, gluTessCallback, gluTessVertex, \
    gluTessBeginPolygon, gluTessEndPolygon, \
    gluTessBeginContour, gluTessEndContour, \
    GLU_TESS_WINDING_RULE, GLU_TESS_WINDING_NONZERO, \
    GLU_TESS_VERTEX, GLU_TESS_BEGIN, GLU_TESS_END, GLU_TESS_ERROR, GLU_TESS_COMBINE, \
    GL_TRIANGLE_FAN, GL_TRIANGLE_STRIP, GL_TRIANGLES, GL_LINE_LOOP

if platform == "win32":
    from ctypes import WINFUNCTYPE as CFUNCTYPE

_tessellator = gluNewTess()

# Winding rule determines the regions that should be filled and those that should remain unshaded.
# Winding direction is determined by the normal.
gluTessProperty(_tessellator, GLU_TESS_WINDING_RULE, GLU_TESS_WINDING_NONZERO)
gluTessNormal(_tessellator, 0, 0, 1)

# As tessellation proceeds, callback routines are called in a manner 
# similar to OpenGL commands glBegin(), glEdgeFlag*(), glVertex*(), and glEnd().
# The callback functions must be C functions so we need to cast our Python callbacks to C.
_tessellate_callback_type = {
    GLU_TESS_VERTEX  : CFUNCTYPE(None, POINTER(GLvoid)),
    GLU_TESS_BEGIN   : CFUNCTYPE(None, GLenum),
    GLU_TESS_END     : CFUNCTYPE(None),
    GLU_TESS_ERROR   : CFUNCTYPE(None, GLenum),
    GLU_TESS_COMBINE : CFUNCTYPE(None, 
        POINTER(GLdouble), 
        POINTER(POINTER(GLvoid)), 
        POINTER(GLfloat), 
        POINTER(POINTER(GLvoid))) 
}

# One path with a 100 points is somewhere around 15KB.
TESSELLATION_CACHE = 100

class TessellationError(Exception):
    pass

class Tessellate(list):
    """ Tessellation state that stores data from the callback functions
        while tessellate() is processing.
    """
    def __init__(self): 
        self.cache = {}         # Cache of previously triangulated contours
        self.queue = []         # Latest contours appear at the end of the list.
        self.reset()
    def clear(self):
        list.__init__(self, []) # Populated during _tessellate_vertex().
    def reset(self):
        self.clear()
        self.mode      = None   # GL_TRIANGLE_FAN | GL_TRIANGLE_STRIP | GL_TRIANGLES.
        self.triangles = []     # After tessellation, contains lists of (x,y)-vertices,
        self._combined = []     # which can be drawn with glBegin(GL_TRIANGLES) mode.

_tessellate = Tessellate()

def _tessellate_callback(type):
    # Registers a C version of a Python callback function for gluTessCallback().
    def _C(function):
        f = _tessellate_callback_type[type](function)
        gluTessCallback(_tessellator, type, cast(f, _CFUNCTYPE(None)))
        return f
    return _C

@_tessellate_callback(GLU_TESS_BEGIN)
def _tessellate_begin(mode):
    # Called to indicate the start of a triangle.
    _tessellate.mode = mode
    
@_tessellate_callback(GLU_TESS_VERTEX)
def _tessellate_vertex(vertex):
    # Called to define the vertices of triangles created by the tessellation.
    _tessellate.append(list(cast(vertex, POINTER(GLdouble))[0:2]))

@_tessellate_callback(GLU_TESS_END)
def _tessellate_end():
    # Called to indicate the end of a primitive.
    # GL_TRIANGLE_FAN defines triangles with a same origin (pt1).
    if _tessellate.mode in (GL_TRIANGLE_FAN, GL_TRIANGLE_STRIP):
        pt1 = _tessellate.pop(0)
        pt2 = _tessellate.pop(0)
        while _tessellate:
            pt3 = _tessellate.pop(0)
            _tessellate.triangles.extend([pt1, pt2, pt3])
            if _tessellate.mode == GL_TRIANGLE_STRIP: 
                pt1 = pt2
            pt2 = pt3
    elif _tessellate.mode == GL_TRIANGLES:
        _tessellate.triangles.extend(_tessellate)
    elif _tessellate.mode == GL_LINE_LOOP:
        pass
    _tessellate.mode  = None
    _tessellate.clear()
    
@_tessellate_callback(GLU_TESS_COMBINE)
def _tessellate_combine(coords, vertex_data, weights, dataOut):
    # Called when the tessellation detects an intersection.
    x, y, z = coords[0:3]
    data = (GLdouble * 3)(x, y, z)
    dataOut[0] = cast(pointer(data), POINTER(GLvoid))
    _tessellate._combined.append(data)
    
@_tessellate_callback(GLU_TESS_ERROR)
def _tessellate_error(code):
    # Called when an error occurs.
    e, s, i = gluErrorString(code), "", 0
    while e[i]: 
        s += chr(e[i])
        i += 1
    raise TessellationError, s

_cache = {}

def tessellate(contours):
    """ Returns a list of triangulated (x,y)-vertices from the given list of path contours,
        where each contour is a list of (x,y)-tuples.
        The vertices can be drawn with GL_TRIANGLES to render a complex polygon, for example:
        glBegin(GL_TRIANGLES)
        for x, y in tessellate(contours):
            glVertex3f(x, y, 0)
        glEnd()
    """
    id = repr(contours)
    if id in _tessellate.cache:
        return _tessellate.cache[id]
    # Push the given contours to C and call gluTessVertex().
    _tessellate.reset()
    contours = [[(GLdouble * 3)(x, y, 0) for x, y in points] for points in contours]
    gluTessBeginPolygon(_tessellator, None)
    for vertices in contours:
        gluTessBeginContour(_tessellator)
        for v in vertices:
            gluTessVertex(_tessellator, v, v)
        gluTessEndContour(_tessellator)
    gluTessEndPolygon(_tessellator)
    # Update the tessellation cache with the results.
    if len(_tessellate.cache) > TESSELLATION_CACHE:
        del _tessellate.cache[_tessellate.queue.pop(0)]
    _tessellate.queue.append(id)
    _tessellate.cache[id] = _tessellate.triangles
    return _tessellate.triangles
    
tesselate = tessellate # Common spelling error.
