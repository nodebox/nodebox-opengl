# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *
from nodebox.graphics.physics import System, Emitter, Particle, MASS

# 1) An emitter will be firing particles with a constant velocity.
# 2) Drag in the system slows down the particles.
# 3) Gravity then becomes greater than the particles' velocity and they are pulled down.
s = System(gravity=(0, 1.0), drag=0.01)

# The emitter is positioned centrally at the bottom,
# and fires particles upwards in a 30-degrees angle range.
e = Emitter(x=200, y=0, angle=90, strength=10.0, spread=30)
for i in range(100):
    # Particles have random mass and lifespan to make it more interesting and diverse.
    # The MASS constant means that we want the radius of the visual particle
    # to be initialized with the same value as its mass (it's a convenience trick). 
    # This way we can observe how heavier particles respond.
    e.append(Particle(0, 0, mass=random(10,50), radius=MASS, life=random(50,250)))

s.append(e) # Install the emitter in the system.

# Add an obstacle that other particles want to stay away from.

class Obstacle(Particle):
    def draw(self):
        # The only way to style individual particles is to redefine draw() in a subclass.
        # Set the fill color directly for this ellipse, i.e. don't use fill(),
        # because this sets the state and then other particles might use this color too.
        ellipse(self.x, self.y, self.radius*2, self.radius*2, fill=(0,0,0.3,0.1))

obstacle = Obstacle(0, 0, mass=70, radius=70, fixed=True)
s.append(obstacle)
s.force(6, source=obstacle) # Repulsive force from this particle to all others.

def draw(canvas):
    
    background(1)
    
    fill(0,0.5,1,0.1)
    stroke(0,0.3)
    strokewidth(1)
    s.update()
    s.draw()
    
    # Put the obstacle at the mouse position.
    # This way we can play around with the fountain spray.
    obstacle.x = canvas.mouse.x
    obstacle.y = canvas.mouse.y
    
canvas.size = 400, 700
canvas.run(draw)