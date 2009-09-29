# Author: Tom De Smedt <tomdesmedt@organisms.be>
# License: GPL (see LICENSE.txt for details).
# Copyright (c) 2008 by Tom De Smedt.
# Thanks to Prof. F. De Smedt at the Free University of Brussels for the math routines.

from context import BezierPath, PathElement, PathError, Point, MOVETO, LINETO, CURVETO, CLOSE
from math import sqrt, pow

#-----------------------------------------------------------------------------------------------------

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
        by adding the lengths of lineair lines between points at t.
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

# Faster C versions:
try: from extensions.bezier_math import linepoint, linelength, curvepoint, curvelength
except:
    pass

#-----------------------------------------------------------------------------------------------------

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

#-----------------------------------------------------------------------------------------------------

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
        segments = path.segmentlengths(relative=True) 
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
        return PathElement(LINETO, x, y, x, y, x, y)
    elif p1.cmd == LINETO:
        x1, y1 = p1.x, p1.y
        x, y = linepoint(t, x0, y0, x1, y1)
        return PathElement(LINETO, x, y, x, y, x, y)
    elif p1.cmd == CURVETO:
        x3, y3, x1, y1, x2, y2 = p1.x, p1.y, p1.ctrl1.x, p1.ctrl1.y, p1.ctrl2.x, p1.ctrl2.y
        x, y, c1x, c1y, c2x, c2y = curvepoint(t, x0, y0, x1, y1, x2, y2, x3, y3)
        return PathElement(CURVETO, x, y, c1x, c1y, c2x, c2y)
    else:
        raise PathError, "Unknown cmd for p1 %s" % p1
        
def points(path, amount=100):
    """ Returns an iterator with a list of calculated points for the path.
    """
    if len(path) == 0:
        raise PathError, "The given path is empty"
    # The delta value is divided by amount - 1, because we also want the last point (t=1.0)
    # If I wouldn't use amount - 1, I fall one point short of the end.
    # E.g. if amount = 4, I want point at t 0.0, 0.33, 0.66 and 1.0,
    # if amount = 2, I want point at t 0.0 and t 1.0
    try:
        delta = 1.0/(amount-1)
    except ZeroDivisionError:
        delta = 1.0
    for i in xrange(amount):
        yield point(path, delta*i)

#-----------------------------------------------------------------------------------------------------

def contours(path):
    """ Returns a list of contours in the path.
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
            current_contour.curveto(el.ctrl1.x, el.ctrl1.y,
                el.ctrl2.x, el.ctrl2.y, el.x, el.y)
        elif el.cmd == CLOSE:
            current_contour.closepath()
    if not empty:
        contours.append(current_contour)
    return contours

#-----------------------------------------------------------------------------------------------------

def findpath(points, curvature=1.0):
    """ Constructs a path between the given list of points.
        Interpolates the list of points and determines a smooth bezier path betweem them.
        The curvature parameter offers some control on how separate segments are stitched together:
        from straight angles to smooth curves.
        Curvature is only useful if the path has more than  three points.
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

#-----------------------------------------------------------------------------------------------------

def insert_point(path, t):
    """ Returns a path copy with an extra point at t.
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
    
    new_path = BezierPath(None)
    new_path.moveto(path[0].x, path[0].y)
    for j in range(1, len(path)):
        if j == i+1:
            if pt_cmd == CURVETO:
                new_path.curveto(pt_h1x, pt_h1y, pt_c1x, pt_c1y, pt_x, pt_y)
                new_path.curveto(pt_c2x, pt_c2y, pt_h2x, pt_h2y, path[j].x, path[j].y)
            elif pt_cmd == LINETO:
                new_path.lineto(pt_x, pt_y)
                if path[j].cmd != CLOSE:
                    new_path.lineto(path[j].x, path[j].y)
                else:
                    new_path.closepath()
            else:
                raise PathError, "Didn't expect pt_cmd %s here" % pt_cmd
        else:
            if path[j].cmd == MOVETO:
                new_path.moveto(path[j].x, path[j].y)
            if path[j].cmd == LINETO:
                new_path.lineto(path[j].x, path[j].y)
            if path[j].cmd == CURVETO:
                new_path.curveto(path[j].ctrl1.x, path[j].ctrl1.y,
                             path[j].ctrl2.x, path[j].ctrl2.y,
                             path[j].x, path[j].y)
            if path[j].cmd == CLOSE:
                new_path.closepath()
                
    return new_path
