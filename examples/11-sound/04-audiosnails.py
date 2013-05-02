# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *
from nodebox.sound import PD
from math import sqrt

# SCREECHING AUDIO SNAILS!
pd = PD("04-audiosnails.pd", start=True)

class Snail:
    def __init__(self, x, y):
        """ An agent moving around, with a preference towards the corners of the canvas.
        """
        self.x = x
        self.y = y
        self.r = 2
        self.dx = random(-2, 2)     # Snail speed.
        self.dy = random(-2, 2)
        self.vx = random(-0.2, 0.2) # Snail acceleration.
        self.vy = random(-0.2, 0.2)
        self.friction = random(0.4, 0.8) # Applied when changing position.
        # Snail tail stores the previous point and draws a line to it 
        # (the rest of the "tail" is done using background in the main draw()).
        self.tail = []
        self.clr = random(.25,1.0)
        
    def update(self):
        if self.x < self.r:
            self.dx = -self.dx * self.friction
            self.x  = self.r
        if self.x > canvas.width - self.r:
            self.dx = -self.dx * self.friction
            self.x  = canvas.width - self.r
        if self.y > canvas.height - self.r:
            self.dy = -self.dy * self.friction
            self.y  = canvas.height - self.r
        if self.y < self.r:
            self.dy = -self.dy * self.friction
            self.y  = self.r
        self.dx = self.dx + self.vx / 5.0
        self.dy = self.dy + self.vy / 5.0
        self.x  = self.x + self.dx
        self.y  = self.y +self.dy
        self.tail.append((self.x, self.y))
        if len(self.tail) > 2:
            del(self.tail[0])
            
    def draw(self):
        stroke(self.clr, 0.5, 1.0-self.clr, 0.85)
        fill(0.5*self.clr, 0.25, 1.0-self.clr, 0.4)
        line(self.x, self.y, self.tail[0][0], self.tail[0][1])
        ellipse(self.x, self.y, self.r*2, self.r*2)

class Attractor:
    
    def __init__(self, x, y):
        """ A moveable attraction field.
            Snails passing through the attractor bend, accellerate and change audio pitch/LFO.
        """
        self.x      = x
        self.y      = y
        self.dmin   = 10
        self.dmax   = 250
        self.mass   = 5000
        self.count  = 0 # Number of snails inside the attractor, controls audio pitch.
        self.weight = 0 # Based on attractor mass and snail distance, controls audio LFO.
        
    def update(self, snails=[]):
        self.value = 0
        self.count = 0
        for i, snail in enumerate(snails):
            dx = self.x - snail.x
            dy = self.y - snail.y
            d  = sqrt(dx*dx + dy*dy) # Snail-Attractor distance.
            if d > self.dmin and d < self.dmax:
                snail.vx += self.mass * dx / d**3 / 5.0
                snail.vy += self.mass * dy / d**3 / 5.0
                self.weight += self.mass * dx / d**3 / 0.01
                self.count  += 1
                
    def draw(self):
        fill(0, 0.025)
        stroke(1, 0.025)
        ellipse(self.x, self.y, 250, 250)
        

attractor = Attractor(200, 200)
snails = []
for i in range(50):
    snails.append(Snail(
        x = random(canvas.width),
        y = random(canvas.height)))
        
def draw(canvas):
    background(0.2, 0.1, 0.2, 0.1)
    # Move the attractor around with the mouse:
    attractor.x = canvas.mouse.x
    attractor.y = canvas.mouse.y
    attractor.update(snails)
    attractor.draw()
    # Draw the snails:
    for snail in snails:
        snail.update()
        snail.draw()
    # Send the attractor's "weight" and snail count to Pd.
    # These control the audio's LFO and pitch respectively.
    pd.send([attractor.weight, attractor.count], "/input", port=44001)
    # Polling for output and drawing text slows everything down.
    # I noticed that Pd no longer responds when too many pd.send() calls are issued too fast.
    # Don't know why (yet).
    fill(1)
    text(pd.output or " ", 10, 10, fontsize=7, fill=(1,1,1,1))

def stop(canvas):
    # Kill the Pd background process.
    pd.stop()

canvas.fps = 30
canvas.size = 600, 400
canvas.run(draw, stop=stop)