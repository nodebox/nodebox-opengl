from nodeboxgl.graphics import *
from nodeboxgl.graphics.geometry import distance
from math import sqrt

def spider(string, x=0, y=0, radius=25, **kwargs):
    """ A path filter that creates web threading along the characters of the given string.
        Its output can be drawn directly to the canvas or used in a render() function.
        Adapted from: http://nodebox.net/code/index.php/Path_Filters
    """
    # **kwargs represents any additional optional parameters.
    # For example: spider("hello", 100, 100, font="Helvetica") =>
    # kwargs = {"font": "Helvetica"}
    # We pass these on to the textpath() call in the function; 
    # so the spider() function takes the same parameters as textpath: 
    # x, y, font, fontsize, fontweight, ...
    font(
        kwargs.get("font", "Droid Sans"),
        kwargs.get("fontsize", 100))
    p = textpath(string, x, y, **kwargs)
    n = int(p.length)
    m = 2.0
    radius = max(radius, 0.1 * fontsize())
    points = list(p.points(n))
    for i in range(n):
        pt1 = choice(points)
        pt2 = choice(points)
        while distance(pt1.x, pt1.y, pt2.x, pt2.y) > radius:
            pt2  = choice(points)      
        line(pt1.x + random(-m, m), 
             pt1.y + random(-m, m),
             pt2.x + random(-m, m), 
             pt2.y + random(-m, m))

# Render the function's output to an image.
# Rendering the image beforehand is much faster than calling spider() every frame.
stroke(0.1, 0.1, 0, 0.5)
strokewidth(1)
img = render(spider, 500, 150, 
    string = "SPIDER",     
      font = "Droid Sans", 
  fontsize = 100, 
      bold = True,
         x = 25,
         y = 25,
    radius = 30)

def draw(canvas):
    canvas.clear()
    translate(0, 200)
    image(img)

canvas.size = 500, 500
canvas.run(draw)
