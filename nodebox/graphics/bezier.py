#=== BEZIER ==========================================================================================
# Bezier mathematics.
# Authors: Tom De Smedt
# License: BSD (see LICENSE.txt for details).
# Copyright (c) 2008 City In A Bottle (cityinabottle.org)
# http://cityinabottle.org/nodebox

# Thanks to Prof. F. De Smedt at the Vrije Universiteit Brussel.

from context import BezierPath, PathElement, PathError, Point, MOVETO, LINETO, CURVETO, CLOSE
from math import sqrt, pow

class DynamicPathElement(PathElement):
    # Not a "fixed" point in the BezierPath, but calculated with BezierPath.point().
    pass

#=====================================================================================================

#--- BEZIER MATH ------------------------------------------------------------------------------------

def linepoint(t, x0, y0, x1, y1):
    """ Returns coordinates for point at t on the line.
        Calculates the coordinates of x and y for a point at t on a straight line.
        The t parameter is a number between 0.0 and 1.0,
        x0 and y0 define the starting point of the line, 
        x1 and y1 the ending point of the line.
    """
    out_x = x0 + t * (x1-x0)
    out_y = y0 + t * (y1-y0)
    return (out_x, out_y)

def linelength(x0, y0, x1, y1):
    """ Returns the length of the line.
    """
    a = pow(abs(x0 - x1), 2)
    b = pow(abs(y0 - y1), 2)
    return sqrt(a+b)

def curvepoint(t, x0, y0, x1, y1, x2, y2, x3, y3, handles=False):
    """ Returns coordinates for point at t on the spline.
        Calculates the coordinates of x and y for a point at t on the cubic bezier spline, 
        and its control points, based on the de Casteljau interpolation algorithm.
        The t parameter is a number between 0.0 and 1.0,
        x0 and y0 define the starting point of the spline,
        x1 and y1 its control point,
        x3 and y3 the ending point of the spline,
        x2 and y2 its control point.
        If the handles parameter is set, returns not only the point at t,
        but the modified control points of p0 and p3 should this point split the path as well.
    """
    mint = 1 - t
    x01 = x0 * mint + x1 * t
    y01 = y0 * mint + y1 * t
    x12 = x1 * mint + x2 * t
    y12 = y1 * mint + y2 * t
    x23 = x2 * mint + x3 * t
    y23 = y2 * mint + y3 * t
    out_c1x = x01 * mint + x12 * t
    out_c1y = y01 * mint + y12 * t
    out_c2x = x12 * mint + x23 * t
    out_c2y = y12 * mint + y23 * t
    out_x = out_c1x * mint + out_c2x * t
    out_y = out_c1y * mint + out_c2y * t
    if not handles:
        return (out_x, out_y, out_c1x, out_c1y, out_c2x, out_c2y)
    else:
        return (out_x, out_y, out_c1x, out_c1y, out_c2x, out_c2y, x01, y01, x23, y23)

def curvelength(x0, y0, x1, y1, x2, y2, x3, y3, n=20):
    """ Returns the length of the spline.
        Integrates the estimated length of the cubic bezier spline defined by x0, y0, ... x3, y3, 
        by adding the lengths of linear lines between points at t.
        The number of points is defined by n 
        (n=10 would add the lengths of lines between 0.0 and 0.1, between 0.1 and 0.2, and so on).
        The default n=20 is fine for most cases, usually resulting in a deviation of less than 0.01.
    """
    length = 0
    xi = x0
    yi = y0
    for i in range(n):
        t = 1.0 * (i+1) / n
        pt_x, pt_y, pt_c1x, pt_c1y, pt_c2x, pt_c2y = \
            curvepoint(t, x0, y0, x1, y1, x2, y2, x3, y3)
        c = sqrt(pow(abs(xi-pt_x),2) + pow(abs(yi-pt_y),2))
        length += c
        xi = pt_x
        yi = pt_y
    return length

# Fast C implementations:
try: from nodebox.ext.bezier import linepoint, linelength, curvepoint, curvelength
except:
    pass

#--- BEZIER PATH LENGTH ------------------------------------------------------------------------------

def segment_lengths(path, relative=False, n=20):
    """ Returns a list with the lengths of each segment in the path.
    """
    lengths = []
    first = True
    for el in path:
        if first == True:
            close_x, close_y = el.x, el.y
            first = False
        elif el.cmd == MOVETO:
            close_x, close_y = el.x, el.y
            lengths.append(0.0)
        elif el.cmd == CLOSE:
            lengths.append(linelength(x0, y0, close_x, close_y))
        elif el.cmd == LINETO:
            lengths.append(linelength(x0, y0, el.x, el.y))
        elif el.cmd == CURVETO:
            x3, y3, x1, y1, x2, y2 = el.x, el.y, el.ctrl1.x, el.ctrl1.y, el.ctrl2.x, el.ctrl2.y
            lengths.append(curvelength(x0, y0, x1, y1, x2, y2, x3, y3, n))
        if el.cmd != CLOSE:
            x0 = el.x
            y0 = el.y
    if relative:
        length = sum(lengths)
        try:
            # Relative segment lengths' sum is 1.0.
            return map(lambda l: l / length, lengths)
        except ZeroDivisionError: 
            # If the length is zero, just return zero for all segments
            return [0.0] * len(lengths)
    else:
        return lengths

def length(path, segmented=False, n=20):
    """ Returns the length of the path.
        Calculates the length of each spline in the path, using n as a number of points to measure.
        When segmented is True, returns a list containing the individual length of each spline
        as values between 0.0 and 1.0, defining the relative length of each spline
        in relation to the total path length.
    """
    if not segmented:
        return sum(segment_lengths(path, n=n), 0.0)
    else:
        return segment_lengths(path, relative=True, n=n)

#--- BEZIER PATH POINT -------------------------------------------------------------------------------

def _locate(path, t, segments=None):
    """ Locates t on a specific segment in the path.
        Returns (index, t, PathElement)
        A path is a combination of lines and curves (segments).
        The returned index indicates the start of the segment that contains point t.
        The returned t is the absolute time on that segment,
        in contrast to the relative t on the whole of the path.
        The returned point is the last MOVETO, any subsequent CLOSETO after i closes to that point.
        When you supply the list of segment lengths yourself, as returned from length(path, segmented=True), 
        point() works about thirty times faster in a for-loop since it doesn't need to recalculate 
        the length during each iteration. 
    """
    if segments == None:
        segments = segment_lengths(path, relative=True) 
    if len(segments) == 0:
        raise PathError, "The given path is empty"
    for i, el in enumerate(path):
        if i == 0 or el.cmd == MOVETO:
            closeto = Point(el.x, el.y)
        if t <= segments[i] or i == len(segments)-1: 
            break
        else: 
            t -= segments[i]
    try: t /= segments[i]
    except ZeroDivisionError: 
        pass
    if i == len(segments)-1 and segments[i] == 0: i -= 1
    return (i, t, closeto)

def point(path, t, segments=None):
    """ Returns coordinates for point at t on the path.
        Gets the length of the path, based on the length of each curve and line in the path.
        Determines in what segment t falls. Gets the point on that segment.
        When you supply the list of segment lengths yourself, as returned from length(path, segmented=True), 
        point() works about thirty times faster in a for-loop since it doesn't need to recalculate 
        the length during each iteration.
    """
    if len(path) == 0:
        raise PathError, "The given path is empty"
    i, t, closeto = _locate(path, t, segments=segments)
    x0, y0 = path[i].x, path[i].y
    p1 = path[i+1]
    if p1.cmd == CLOSE:
        x, y = linepoint(t, x0, y0, closeto.x, closeto.y)
        return DynamicPathElement(LINETO, ((x, y),))
    elif p1.cmd == LINETO:
        x1, y1 = p1.x, p1.y
        x, y = linepoint(t, x0, y0, x1, y1)
        return DynamicPathElement(LINETO, ((x, y),))
    elif p1.cmd == CURVETO:
        # Note: the handles need to be interpreted differenty than in a BezierPath.
        # In a BezierPath, ctrl1 is how the curve started, and ctrl2 how it arrives in this point.
        # Here, ctrl1 is how the curve arrives, and ctrl2 how it continues to the next point.
        x3, y3, x1, y1, x2, y2 = p1.x, p1.y, p1.ctrl1.x, p1.ctrl1.y, p1.ctrl2.x, p1.ctrl2.y
        x, y, c1x, c1y, c2x, c2y = curvepoint(t, x0, y0, x1, y1, x2, y2, x3, y3)
        return DynamicPathElement(CURVETO, ((c1x, c1y), (c2x, c2y), (x, y)))
    else:
        raise PathError, "Unknown cmd '%s' for p1 %s" % (p1.cmd, p1)
        
def points(path, amount=100, start=0.0, end=1.0, segments=None):
    """ Returns an iterator with a list of calculated points for the path.
        To omit the last point on closed paths: end=1-1.0/amount
    """
    if len(path) == 0:
        raise PathError, "The given path is empty"
    n = end - start
    d = n
    if amount > 1: 
        # The delta value is divided by amount-1, because we also want the last point (t=1.0)
        # If we don't use amount-1, we fall one point short of the end.
        # If amount=4, we want the point at t 0.0, 0.33, 0.66 and 1.0.
        # If amount=2, we want the point at t 0.0 and 1.0.
        d = float(n) / (amount-1)
    for i in xrange(amount):
        yield point(path, start+d*i, segments)

#--- BEZIER PATH CONTOURS ----------------------------------------------------------------------------

def contours(path):
    """ Returns a list of contours in the path, as BezierPath objects.
        A contour is a sequence of lines and curves separated from the next contour by a MOVETO.
        For example, the glyph "o" has two contours: the inner circle and the outer circle.
    """
    contours = []
    current_contour = None
    empty = True
    for i, el in enumerate(path):
        if el.cmd == MOVETO:
            if not empty:
                contours.append(current_contour)
            current_contour = BezierPath()
            current_contour.moveto(el.x, el.y)
            empty = True
        elif el.cmd == LINETO:
            empty = False
            current_contour.lineto(el.x, el.y)
        elif el.cmd == CURVETO:
            empty = False
            current_contour.curveto(el.ctrl1.x, el.ctrl1.y, el.ctrl2.x, el.ctrl2.y, el.x, el.y)
        elif el.cmd == CLOSE:
            current_contour.closepath()
    if not empty:
        contours.append(current_contour)
    return contours

#--- BEZIER PATH FROM POINTS -------------------------------------------------------------------------

def findpath(points, curvature=1.0):
    """ Constructs a smooth BezierPath from the given list of points.
        The curvature parameter offers some control on how separate segments are stitched together:
        from straight angles to smooth curves.
        Curvature is only useful if the path has more than three points.
    """
    
    # The list of points consists of Point objects,
    # but it shouldn't crash on something straightforward
    # as someone supplying a list of (x,y)-tuples.
    from types import TupleType
    for i, pt in enumerate(points):
        if type(pt) == TupleType:
            points[i] = Point(pt[0], pt[1])
    
    # No points: return nothing.
    if len(points) == 0: return None
    # One point: return a path with a single MOVETO-point.
    if len(points) == 1:
        path = BezierPath(None)
        path.moveto(points[0].x, points[0].y)
        return path
    # Two points: path with a single straight line.
    if len(points) == 2:
        path = BezierPath(None)
        path.moveto(points[0].x, points[0].y)
        path.lineto(points[1].x, points[1].y)
        return path
    # Zero curvature means path with straight lines.
    curvature = max(0, min(1, curvature))
    if curvature == 0:
        path = BezierPath(None)
        path.moveto(points[0].x, points[0].y)
        for i in range(len(points)): 
            path.lineto(points[i].x, points[i].y)
        return path
    
    # Construct the path with curves.
    curvature = 4 + (1.0-curvature)*40
    
    # The first point's ctrl1 and ctrl2 and last point's ctrl2
    # will be the same as that point's location;
    # we cannot infer how the path curvature started or will continue.
    dx = {0: 0, len(points)-1: 0}
    dy = {0: 0, len(points)-1: 0}
    bi = {1: -0.25}
    ax = {1: (points[2].x-points[0].x-dx[0]) / 4}
    ay = {1: (points[2].y-points[0].y-dy[0]) / 4}
    for i in range(2, len(points)-1):
        bi[i] = -1 / (curvature + bi[i-1])
        ax[i] = -(points[i+1].x-points[i-1].x-ax[i-1]) * bi[i]
        ay[i] = -(points[i+1].y-points[i-1].y-ay[i-1]) * bi[i]
        
    r = range(1, len(points)-1)
    r.reverse()
    for i in r:
        dx[i] = ax[i] + dx[i+1] * bi[i]
        dy[i] = ay[i] + dy[i+1] * bi[i]

    path = BezierPath(None)
    path.moveto(points[0].x, points[0].y)
    for i in range(len(points)-1):
        path.curveto(points[i].x + dx[i], 
                     points[i].y + dy[i],
                     points[i+1].x - dx[i+1], 
                     points[i+1].y - dy[i+1],
                     points[i+1].x,
                     points[i+1].y)
    
    return path

#--- BEZIER PATH INSERT POINT ------------------------------------------------------------------------

def insert_point(path, t):
    """ Inserts an extra point at t.
    """
    
    # Find the points before and after t on the path.
    i, t, closeto = _locate(path, t)
    x0 = path[i].x
    y0 = path[i].y
    p1 = path[i+1]
    p1cmd, x3, y3, x1, y1, x2, y2 = p1.cmd, p1.x, p1.y, p1.ctrl1.x, p1.ctrl1.y, p1.ctrl2.x, p1.ctrl2.y
    
    # Construct the new point at t.
    if p1cmd == CLOSE:
        pt_cmd = LINETO
        pt_x, pt_y = linepoint(t, x0, y0, closeto.x, closeto.y)
    elif p1cmd == LINETO:
        pt_cmd = LINETO
        pt_x, pt_y = linepoint(t, x0, y0, x3, y3)
    elif p1cmd == CURVETO:
        pt_cmd = CURVETO
        pt_x, pt_y, pt_c1x, pt_c1y, pt_c2x, pt_c2y, pt_h1x, pt_h1y, pt_h2x, pt_h2y = \
            curvepoint(t, x0, y0, x1, y1, x2, y2, x3, y3, True)
    else:
        raise PathError, "Locate should not return a MOVETO"

    # NodeBox for OpenGL modifies the path in place,
    # NodeBox for Mac OS X returned a path copy (see inactive code below).
    if pt_cmd == CURVETO:
        path[i+1].ctrl1.x = pt_c2x
        path[i+1].ctrl1.y = pt_c2y
        path[i+1].ctrl2.x = pt_h2x
        path[i+1].ctrl2.y = pt_h2y
        path.insert(i+1, PathElement(cmd=CURVETO, pts=[(pt_h1x, pt_h1y), (pt_c1x, pt_c1y), (pt_x, pt_y)]))
    elif pt_cmd == LINETO:
        path.insert(i+1, PathElement(cmd=LINETO, pts=[(pt_x, pt_y)]))
    else:
        raise PathError, "Didn't expect pt_cmd %s here" % pt_cmd
    return path[i+1]
    
    #new_path = BezierPath(None)
    #new_path.moveto(path[0].x, path[0].y)
    #for j in range(1, len(path)):
    #    if j == i+1:
    #        if pt_cmd == CURVETO:
    #            new_path.curveto(pt_h1x, pt_h1y, pt_c1x, pt_c1y, pt_x, pt_y)
    #            new_path.curveto(pt_c2x, pt_c2y, pt_h2x, pt_h2y, path[j].x, path[j].y)
    #        elif pt_cmd == LINETO:
    #            new_path.lineto(pt_x, pt_y)
    #            if path[j].cmd != CLOSE:
    #                new_path.lineto(path[j].x, path[j].y)
    #            else:
    #                new_path.closepath()
    #        else:
    #            raise PathError, "Didn't expect pt_cmd %s here" % pt_cmd
    #    else:
    #        if path[j].cmd == MOVETO:
    #            new_path.moveto(path[j].x, path[j].y)
    #        if path[j].cmd == LINETO:
    #            new_path.lineto(path[j].x, path[j].y)
    #        if path[j].cmd == CURVETO:
    #            new_path.curveto(path[j].ctrl1.x, path[j].ctrl1.y,
    #                         path[j].ctrl2.x, path[j].ctrl2.y,
    #                         path[j].x, path[j].y)
    #        if path[j].cmd == CLOSE:
    #            new_path.closepath()
                
    return new_path

#=====================================================================================================

#--- BEZIER ARC --------------------------------------------------------------------------------------

# Copyright (c) 2005-2008, Enthought, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice, 
# this list of conditions and the following disclaimer.
# Redistributions in binary form must reproduce the above copyright notice, 
# this list of conditions and the following disclaimer in the documentation 
# and/or other materials provided with the distribution.
# Neither the name of Enthought, Inc. nor the names of its contributors 
# may be used to endorse or promote products derived from this software 
# without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
# IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, 
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; 
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, 
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY 
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from math import acos, sin, cos, hypot, ceil, sqrt, radians, degrees

def arc(x1, y1, x2, y2, angle=0, extent=90):
    """ Compute a cubic Bezier approximation of an elliptical arc.
        (x1, y1) and (x2, y2) are the corners of the enclosing rectangle.
        The coordinate system has coordinates that increase to the right and down.
        Angles, measured in degrees, start with 0 to the right (the positive X axis) 
        and increase counter-clockwise.
        The arc extends from angle to angle+extent.
        I.e. angle=0 and extent=180 yields an openside-down semi-circle.
        The resulting coordinates are of the form (x1,y1, x2,y2, x3,y3, x4,y4)
        such that the curve goes from (x1, y1) to (x4, y4) 
        with (x2, y2) and (x3, y3) as their respective Bezier control points.
    """
    x1, y1, x2, y2 = min(x1,x2), max(y1,y2), max(x1,x2), min(y1,y2)
    extent = min(max(extent, -360), 360)
    n = abs(extent) <= 90 and 1 or int(ceil(abs(extent) / 90.0))
    a = float(extent) / n
    cx = float(x1 + x2) / 2
    cy = float(y1 + y2) / 2
    rx = float(x2 - x1) / 2
    ry = float(y2 - y1) / 2
    a2 = radians(a) / 2
    kappa = abs(4.0 / 3 * (1 - cos(a2)) / sin(a2))
    points = []
    for i in range(n):
        theta0 = radians(angle + (i+0) * a)
        theta1 = radians(angle + (i+1) * a)
        c0, c1 = cos(theta0), cos(theta1)
        s0, s1 = sin(theta0), sin(theta1)
        k = a > 0 and -kappa or kappa
        points.append((
            cx + rx * c0,
            cy - ry * s0,
            cx + rx * (c0 + k * s0),
            cy - ry * (s0 - k * c0),
            cx + rx * (c1 - k * s1),
            cy - ry * (s1 + k * c1),
            cx + rx * c1,
            cy - ry * s1
        ))
    return points

def arcto(x1, y1, rx, ry, phi, large_arc, sweep, x2, y2):
    """ An elliptical arc approximated with Bezier curves or a line segment.
        Algorithm taken from the SVG 1.1 Implementation Notes:
        http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes
    """
    
    def angle(x1, y1, x2, y2):
        a = degrees(acos(min(max((x1*x2 + y1*y2) / hypot(x1,y1) * hypot(x2,y2), -1), 1)))
        return x1*y2 > y1*x2 and a or -a
        
    def abspt(x, y, cphi, sphi, mx, my):
        return (x * cp - y * sp + mx, 
                x * sp + y * cp + my)
    
    if x1 == x2 and y1 == y2:
        return []
    if rx == 0 or ry == 0: # Line segment.
        return [(x2,y2)]
    rx, ry, phi = abs(rx), abs(ry), phi % 360
    cp = cos(radians(phi))
    sp = sin(radians(phi))

    # Rotate to the local coordinates.
    dx = 0.5 * (x1 - x2)
    dy = 0.5 * (y1 - y2)
    x  =  cp * dx + sp * dy
    y  = -sp * dx + cp * dy
    
    # If rx, ry and phi are such that there is no solution 
    # (basically, the ellipse is not big enough to reach from (x1, y1) to (x2, y2)) 
    # then the ellipse is scaled up uniformly until there is exactly one solution 
    # (until the ellipse is just big enough).
    s = (x/rx)**2 + (y/ry)**2
    if s > 1.0:
        s = sqrt(s); rx, ry = rx*s, ry*s

    # Solve for the center in the local coordinates.
    a = sqrt(max((rx*ry)**2 - (rx*y)**2 - (ry*x)**2, 0) / ((rx*y)**2 + (ry*x)**2))
    a = large_arc == sweep and -a or a 
    cx =  a * rx * y / ry
    cy = -a * ry * x / rx

    # Transform back.
    mx = 0.5 * (x1 + x2)
    my = 0.5 * (y1 + y2)

    # Compute the start angle and the angular extent of the arc.
    # Note that theta is local to the phi-rotated coordinate space.
    dx1 = ( x - cx) / rx
    dy1 = ( y - cy) / ry
    dx2 = (-x - cx) / rx
    dy2 = (-y - cy) / ry
    theta = angle(1.0, 0.0, dx1, dy1)
    delta = angle(dx1, dy1, dx2, dy2)
    if not sweep and delta > 0: delta -= 360
    if sweep and delta < 0: delta += 360

    # Break it apart into Bezier curves.
    points  = []
    handles = arc(cx-rx, cy-ry, cx+rx, cy+ry, theta, delta)
    for x1, y1, x2, y2, x3, y3, x4, y4 in handles:
        points.append((
            abspt(x2, y2, cp, sp, mx, my) + \
            abspt(x3, y3, cp, sp, mx, my) + \
            abspt(x4, y4, cp, sp, mx, my)
        ))
    return points
