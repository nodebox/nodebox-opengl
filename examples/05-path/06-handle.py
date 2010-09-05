# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *

# I always seem to forget how Bezier handles work.
# This example clarifies which handles control what part of a curve.

fontsize(9)

p = BezierPath()
p.moveto(50, 100)
p.curveto(100, 400, 200, 50, 450, 100)

def draw(canvas):

    canvas.clear()
    
    nofill()
    stroke(0, 0.25)
    strokewidth(1)
    drawpath(p)
    fill(0)
    
    # BezierPath is essentially a list of PathElement objects.
    # Each PathElement has a "cmd" property (MOVETO, LINETO, CURVETO or CLOSE),
    # an x and y position and two control handles ctrl1 and ctrl2.
    # These control handles determine how a curve bends.
    for i, pt in enumerate(p):
        if i > 0:
            # ctrl1 describes how the curve from the previous point started.
            line(p[i-1].x, p[i-1].y, pt.ctrl1.x, pt.ctrl1.y, strokestyle=DASHED)
            text("pt%s.ctrl1 (%s,%s)" % (i, pt.ctrl1.x, pt.ctrl1.y), 
                x = pt.ctrl1.x, 
                y = pt.ctrl1.y+5)
        if pt.ctrl2.x != pt.x \
        or pt.ctrl2.y != pt.y:
            # ctrl2 describes how the curve from the previous point arrives in this point.
            line(pt.x, pt.y, pt.ctrl2.x, pt.ctrl2.y, strokestyle=DASHED)
            t = text("pt%s.ctrl2 (%s,%s)" % (i, pt.ctrl2.x, pt.ctrl2.y), 
                x = pt.ctrl2.x, 
                y = pt.ctrl2.y+5)
        ellipse(pt.x, pt.y, 4, 4)
        text("pt%s"%i, x=pt.x+5, y=pt.y+5)
    
    # If you use BezierPath.points() to generate intermediary points,
    # you get DynamicPathElements whose handles need to be interpreted differently:
    # - ctrl1 describes how the curve from the previous point arrives,
    # - ctrl2 describes how the curve continues.
    t = canvas.frame % 500 * 0.002
    pt = p.point(t)
    ellipse(pt.x, pt.y, 4, 4)
    line(pt.x, pt.y, pt.ctrl1.x, pt.ctrl1.y, strokestyle=DASHED)
    line(pt.x, pt.y, pt.ctrl2.x, pt.ctrl2.y, strokestyle=DASHED)
    text("ptx", x=pt.x+5, y=pt.y+5)
    text("ptx.ctrtl1", x=pt.ctrl1.x, y=pt.ctrl1.y+5)
    text("ptx.ctrtl2", x=pt.ctrl2.x, y=pt.ctrl2.y+5)
        
canvas.size = 500, 500
canvas.run(draw)