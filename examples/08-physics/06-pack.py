import os
from nodeboxgl.graphics import * 
from nodeboxgl.graphics.geometry import distance, angle, smoothstep

# Circle-packing algorithm.
# This script was used to produce one of the panels in NANOPHYSICAL:
# http://nodebox.net/code/index.php/Nanophysical

class Circle:
    
    def __init__(self, x, y, radius, image=None):
        """ An object that can be passed to pack(), 
            with a repulsion radius and an image to draw inside the radius.
        """
        self.x = x
        self.y = y
        self.radius = radius
        self.image = image
        self.goal = Point(x,y)
       
    def contains(self, x, y):
        return distance(self.x, self.y, x, y) <= self.radius
        
    def draw(self):
        a = angle(self.x, self.y, self.goal.x, self.goal.y)
        r = self.radius * 1.25 # Let the cells overlap a little bit.
        push()
        translate(self.x, self.y)
        scale(r*2 / min(self.image.width, self.image.height))
        rotate(a)
        image(self.image, x=-r, y=-r) # Rotate from image center.
        pop()
 
def pack(circles, x, y, padding=2, exclude=[]):
    """ Circle-packing algorithm.
        Groups the given list of Circle objects around (x,y) in an organic way.
    """
    # Ported from Sean McCullough's Processing code:
    # http://www.cricketschirping.com/processing/CirclePacking1/
    # See also: http://en.wiki.mcneel.com/default.aspx/McNeel/2DCirclePacking
    
    # Repulsive force: move away from intersecting circles.
    for i, circle1 in enumerate(circles):
        for circle2 in circles[i+1:]:
            d = distance(circle1.x, circle1.y, circle2.x, circle2.y)
            r = circle1.radius + circle2.radius + padding
            if d < r - 0.01:
                dx = circle2.x - circle1.x
                dy = circle2.y - circle1.y
                vx = (dx / d) * (r-d) * 0.5
                vy = (dy / d) * (r-d) * 0.5
                if circle1 not in exclude:
                    circle1.x -= vx
                    circle1.y -= vy
                if circle2 not in exclude:
                    circle2.x += vx
                    circle2.y += vy
    
    # Attractive force: move all circles to center.
    for circle in circles:
        circle.goal.x = x
        circle.goal.y = y
        if circle not in exclude:
            damping = circle.radius ** 3 * 0.000001 # Big ones in the middle.
            vx = (circle.x - x) * damping
            vy = (circle.y - y) * damping
            circle.x -= vx
            circle.y -= vy

def cell(t):
    # Returns a random PNG-image from cells/
    # Some cells occur more frequently than others:
    # t is a number between 0.0 and 1.0 that determines which image to pick.
    # This is handy when combined with smoothstep(), 
    # then we can put a preference on empty blue cells,
    # while still ensuring that some of each cell appear.
    if t < 0.4: 
        img = choice([
            "green-empty1.png", 
            "green-empty2.png", 
            "green-empty3.png"] + [
            "green-block1.png", 
            "green-block2.png"] * 2)
    elif t < 0.5: 
        img = choice([
            "green-circle1.png", 
            "green-circle2.png"])
    elif t < 0.6: 
        img = choice([
            "green-star1.png", 
            "green-star2.png"])
    else: 
        img = choice([
            "blue-block.png",
            "blue-circle.png",
            "blue-star.png"] + [
            "blue-empty1.png", 
            "blue-empty2.png"] * 5)
    return Image(os.path.join("cells", img))

circles = []
def setup(canvas):
    n = 60
    global circles; circles = []
    for i in range(n):
        # Create a group of n cells.
        # Smoothstep yields more numbers near 1.0 than near 0.0, 
        # so we'll got mostly empty blue cells.
        t = smoothstep(0, n, i)
        circles.append(
            Circle(x = random(-100), # Start offscreen to the left.
                   y = random(canvas.height), 
              radius = 10 + 0.5 * t*i, # Make the blue cells bigger.
               image = cell(t)))

dragged = None
def draw(canvas):
    
    background(1)
    
    # Cells can be dragged:
    global dragged
    if dragged:
        dragged.x = canvas.mouse.x
        dragged.y = canvas.mouse.y
    if not canvas.mouse.pressed:
        dragged = None
    elif not dragged:
        for circle in circles:
            if circle.contains(canvas.mouse.x, canvas.mouse.y): 
                dragged = circle; break
    
    for circle in circles:
        circle.draw()
    
    pack(circles, 300, 300, exclude=[dragged])
     
canvas.size = 600, 600
canvas.run(draw, setup)
