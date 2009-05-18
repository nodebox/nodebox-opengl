# 2D geometry functions.
# Authors: Tom De Smedt
# License: GPL (see LICENSE.txt for details).
# Copyright (c) 2008 City In A Bottle (cityinabottle.org)

from math import sqrt, pow
from math import sin, cos, atan2, degrees, radians, pi

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

def rotate(x, y, x0, y0, degrees):
    """ Returns the coordinates of (x,y) rotated around origin (x0,y0).
    """
    x, y = x-x0, y-y0
    a, b = cos(radians(degrees)), sin(radians(degrees))
    return (x*a-y*b+x0, y*a+x*b+y0)

def reflect(x0, y0, x1, y1, d=1.0, a=180):
    """ Returns the reflection of a point through origin (x0,y0).
    """
    return coordinates(x0, y0, d*distance(x0,y0,x1,y1), a+angle(x0,y0,x1,y1))

#--- INTERSECTION ------------------------------------------------------------------------------------

def line_line_intersection(x1, y1, x2, y2, x3, y3, x4, y4, infinite=False):
    """ Determines the intersection point of two lines, or two finite line segments if infinite=False.
    When the lines do not intersect, returns (None, None).
    P. Bourke, http://local.wasp.uwa.edu.au/~pbourke/geometry/lineline2d/
    """
    ua = (x4-x3)*(y1-y3) - (y4-y3)*(x1-x3)
    ub = (x2-x1)*(y1-y3) - (y2-y1)*(x1-x3)
    d  = (y4-y3)*(x2-x1) - (x4-x3)*(y2-y1)
    if d == 0:
        if ua == ub == 0:
            # The lines are coincident
            return None, None
        else:
            # The lines are parallel.
            return None, None
    ua /= float(d)
    ub /= float(d)
    if not infinite and not (0<=ua<=1 and 0<=ub<=1):
        # Intersection point is not within both line segments.
        return None, None
    return (x1+ua*(x2-x1), y1+ua*(y2-y1))
    
def circle_line_intersection(cx, cy, radius, x1, y1, x2, y2, infinite=False):
	""" Returns a list of points where the circle and the line intersect.
	Returns an empty list when the circle and the line do not intersect.
	http://www.vb-helper.com/howto_net_line_circle_intersections.html
	"""	
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
    for i in xrange(n):
        j = i<n-1 and i+1 or 0
        x0, y0 = points[i][0], points[i][1]
        x1, y1 = points[j][0], points[j][1]
        if (y0 < y and y1 >= y) or (y1 < y and y0 >= y):
            if x0 + (y-y0) / (y1-y0) * (x1-x0) < x:
                odd = not odd
    return odd

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
        from context import BezierPath, LINETO, CURVETO, MOVETO, CLOSE
        p = BezierPath()
        for pt in path:
            if pt.cmd == CLOSE:
                p.closepath()
            elif pt.cmd == MOVETO:
                p.moveto(*self.apply(pt.x, pt.y))
            elif pt.cmd == LINETO:
                p.lineto(*self.apply(pt.x, pt.y))
            elif pt.cmd == CURVETO:
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

#=====================================================================================================

#--- POINT -------------------------------------------------------------------------------------------

class Point:
    
    def __init__(self, x, y):
        self.x = x
        self.y = y
        
    def __repr__(self):
        return "Point(x=%.2f, y=%.2f)" % (self.x, self.y)
        
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
        # Normalize if width or height is negative.
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
        for p in (self.x, self.y, self.width, self.height):
            return p

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
            min(self.y+self.height, b.x+b.height) - my)
    
    def union(self, b):
        """ Returns bounds that encompass the union of the two.
        """
        mx, my = min(self.x, b.x), min(self.y, b.y)
        return Bounds(mx, my, 
            max(self.x+self.width, b.x+b.width) - mx, 
            max(self.y+self.height, b.x+b.height) - my)

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
