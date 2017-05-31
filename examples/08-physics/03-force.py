from nodeboxgl.graphics import *
from nodeboxgl.graphics.physics import Particle, Force, System

# BANG!

# Here is a short example of how the Particle class
# can be subclassed with a custom draw() method:
class Spark(Particle):
    def draw(self):
        r = self.radius * (1-self.age)
        ellipse(self.x, self.y, r*2, r*2)

s = System(gravity=(0, 2.5))        # Pull the particles to the bottom edge.
for i in range(80):
    s.append(
        Spark(
              x = 300, 
              y = 400, 
           mass = random(5.0,10.0), # Heavier particles are repulsed harder.
         radius = 5,                # But doesn't mean they appear bigger.
           life = 200               # Particles whither away after 200 frames.
    ))

# A repulsive force between all particles.
# When particles are very close to each other, forces can be very strong,
# causing particles to move offscreen before anything can be observed.
# This can be tweaked with the threshold (
# which is the minimum distance at which the force operates).
# We can also lower the strength of the force,
# but this weakens the effect in general.
# What also helps is not creating all particles at the same position.
s.force(strength=8.5, threshold=70)

def draw(canvas):
    
    background(1, 0.1) # Trailing effect.
    
    s.update(limit=20)
    s.draw()
canvas.size = 600, 600
canvas.run(draw)

# Running physics in real-time takes a lot of processing power.
# If you are using physics for game effects (e.g. explosions, spells),
# it is a good idea to render them offscreen, store them as an Animation, 
# and replay the animation when necessary.
