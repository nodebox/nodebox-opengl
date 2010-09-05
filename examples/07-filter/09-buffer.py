# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *
from nodebox.graphics.geometry import coordinates
from time import time

flower = Image("cell.png")
shadow = dropshadow(flower, alpha=1.0) # = image(blur(flower), color=(0,0,0,1))
# Each "flower" is drawn with a shadow underneath to add some depth.
# The global shadow layer is at the bottom of the plant.
# Ideally, each growing root would have its own shadow,
# but it is faster this way using only one offscreen buffer for all global shadows
# and a pre-rendered shadow image for each individual flower. 

class Root:
    
    def __init__(self, x, y, angle=90, radius=20, step=60, time=1.0, color=Color(0)):
        self.x      = x
        self.y      = y
        self.angle  = angle
        self.radius = radius # Segment length.
        self.step   = step   # Maximum left or right rotation from current angle.
        self.time   = time
        self.color  = color
        
    def copy(self):
        return Root(
            self.x, 
            self.y, 
            self.angle, 
            self.radius, 
            self.step, 
            self.time, 
            self.color.copy())
        
    def update(self):
        # The performance trick is that we don't keep a history, 
        # e.g. no list with all the previous segments in the growing root.
        # We simply keep the position and heading of the last segment.
        # The previous segments have been rendered in a texture, i.e. they are "frozen".
        self.x, self.y = coordinates(self.x, self.y, self.radius, self.angle)
        self.angle += random(-self.step, self.step)
        self.time *= 0.8 + random(0.2)
        
    def draw(self):
        push()
        translate(self.x, self.y)
        strokewidth(2)
        stroke(
            self.color.r, 
            self.color.g, 
            self.color.b, 
            self.color.a * self.time) # More transparent over time.
        ellipse(0, 0, 
             width = 0.2+ 0.5 * self.time * self.radius, 
            height = 0.2+ 0.5 * self.time * self.radius) # Smaller over time.
        rotate(self.angle)
        line(0, 0, self.radius, 0)
        scale(0.2 + self.time)
        image(shadow, -15, -15, width=20, height=20, alpha=0.5)
        image(flower, -10, -10, width=20, height=20, alpha=0.5, 
            color=(canvas.mouse.relative_x*0.5+0.5, 1, self.time+0.5, 1))
        pop()

CLR = Color(0.27,0.29,0.36)
CLR = lighter(CLR, 0.3)
plant = [Root(200, -50, color=CLR) for i in range(10)]

def grow(plant=[], branch=0.01):
    """ Updates each root in the given list to a new position.
        Roots can branch and will disappear over time.
        Returns the updated list.
    """
    new = []
    for root in plant:
        root.update()
        if root.time > 0.05:
            new.append(root)
        elif len(plant) < 50:
            # Replace the disappeared root with a new one.
            # Vary the time (=lifespan) so new roots appear at irregular intervals.
            x, y, angle = choice((
                (200 + random(50), -50, 90+random(-10,10)),
                #(-50, random(50), 0)
            ))
            new.append(Root(x, y, angle=angle, color=CLR, time=random(0.5, 3.5, bias=0.3)))
        if random() < branch:
            new.append(root.copy())
    return new

# Roots are drawn into an offscreen buffer instead of directly to the screen.
# This way we get an image with a transparent background, which we can use
# to generate a dropshadow on-the-fly.
# The bigger the size of the buffer, the more pixels and the slower it gets.
# We work at a lower resolution and then scale the buffer up to the size of the screen.
RESOLUTION = 0.5
buffer = OffscreenBuffer(
    RESOLUTION * canvas.screen.width, 
    RESOLUTION * canvas.screen.height)

def draw(canvas):
    
    # It takes some juggling with the contrast of the colors to avoid artefacts.
    colorplane(0, 0, canvas.width, canvas.height, 
        lighter(color(0.14, 0.13, 0.18)), 
                color(0.07, 0.06, 0.14), 
                color(0.14, 0.20, 0.18), 
                color(0.07, 0.06, 0.14))

    global plant
    plant = grow(plant)
    
    # Draw each root in the offscreen texture.
    # The texture already contains whatever was drawn in it previous frame.
    buffer.push()
    for root in plant:
        root.draw()
        root.step = canvas.mouse.relative_x * 60
        root.radius = canvas.mouse.relative_y * 30
    buffer.pop()
    
    # Every few frames, make the buffered image more transparent,
    # so that old content fades away.
    if canvas.frame % 2 == 0 and not canvas.mouse.pressed:
        buffer.texture = transparent(buffer.texture, 0.9).texture
        
    # Scale up the buffered image to the screen size.
    # Draw the image with a dropshadow effect.
    # Since the offscreen buffer is scaled, the edges will look rough.
    # Apply a small blur effect to smoothen them.    
    img = buffer.texture
    #img = mirror(img, vertical=True, dx=0.35, dy=0) # Interesting patterns.
    image(dropshadow(img, alpha=1.0, amount=1), 0, -50, 
         width = canvas.width, 
        height = canvas.height+50)
    # Hypnotizing breathing effect:
    img = stretch(img, 0.2, 0.1, radius=0.75, zoom=0.4-cos(canvas.frame*0.01)*0.4)
    image(img, 0, 0,
         width = canvas.width, 
        height = canvas.height,
        )#filter = blurred(scale=0.75))

canvas.fps = 20
canvas.size = 800, 600
canvas.fullscreen = True
canvas.run(draw)