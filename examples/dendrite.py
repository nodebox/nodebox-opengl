# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.append(os.path.join(".."))

from nodebox.graphics import *
from nodebox.graphics.geometry import coordinates

class Branch:
    
    def __init__(self, x, y, angle=0, radius=5):
        self.x = x
        self.y = y
        self.angle = angle
        self.radius = radius
        self.step = 60
        
    def update(self):
        self.x, self.y = coordinates(self.x, self.y, self.radius*4, self.angle)
        self.angle += random(-self.step, self.step)
        
    def draw(self):
        push()
        translate(self.x, self.y)
        ellipse(0, 0, self.radius*2, self.radius*2)
        rotate(self.angle)
        stroke(0)
        line(0, 0, self.radius*4, 0)
        pop()

b = Branch(400, 300)

fbo1 = FBO(800,600)
fbo2 = FBO(800,600)

g = gradient(800, 800, color(0.2,0.25,0), color(0.1,0.1,0), type=RADIAL)

def update(canvas):
    b.update()
    fbo1.push()
    fill(0,0.5)
    b.draw()
    fbo1.pop()

    #fbo2.clear()
    fbo2.push()
    x, b.x = b.x, 50
    y, b.y = b.y, 50
    image(blur(render(b.draw,100,100), amount=4), x-50+canvas.frame%50, y-50)
    b.x = x
    b.y = y
    fbo2.pop()

def draw(canvas):

    canvas.clear()
    image(g, 0, -100)

    #b.update()3
    image(fbo2.texture, 0, 0)
    image(fbo1.texture)
    #b.draw()
    
canvas.size = 800, 600
canvas.run(draw, update=update)