# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *
from nodebox.graphics.physics import Particle, Spring, System

# A "particle system" is used to simulate effects such as explosions, smoke, water, ...
# It consists of object with a mass (particles) that are subjected to forces
# (attractive, repulsive, spring-based).

# In this case,
# the system is a grid (net/tissue) of particles arranged in rows and columns.
s = System()
x = 65 # Horizontal offset.
y = 65 # Vertical offset.
d = 40 # Distance between each particle.
m = 10 # Number of rows.
n = 10 # Number of columns.
for i in range(n):
    for j in range(m):
        s.append(
            Particle(
                x = x + i*d, 
                y = y + j*d, radius=5))

# Spring forces operate on all particles,
# so that when we drag one particle all others are indirectly dragged as well.
# The strength of each spring defines the flexibilty of the resulting fabric.
for i in range(n):
    for j in range(m):
        p1 = s.particles[i*m + j]
        if i < (n-1):
            p2 = s.particles[(i+1)*m + j+0] # Particle to the right.
            s.springs.append( Spring(p1, p2, length=d, strength=2.0))
        if j < (m-1):
            p2 = s.particles[(i+0)*m + j+1] # Particle below.
            s.springs.append( Spring(p1, p2, length=d, strength=2.0))

# An interesting effect is to add a global repulsive force between all particles.
# The fabric will now bulge outward - a little bit like a balloon.
# When manipulated, it will resume its old shape.
#s.force(strength=1)

dragged = None
def draw(canvas):

    canvas.clear()
    background(1)

    stroke(0, 0.2)
    fill(0)
    s.update() # Calculate forces in the system.
    s.draw()   # Draw particles and springs.
               # This is a very simple representation.
               # If you need fancier drawing, subclass Particle and Spring.
    
    # Particles can be dragged... I hate making the bed.
    global dragged
    if dragged:
        # Uncomment the code below to make the fabric break on random occasions.
        # If this happens, find all the springs connected 
        # to the particle being dragged and snap them:
        #if random() > 0.995:
        #    for f in s.dynamics(dragged, type=Spring):
        #        f.snap()
        dragged.x = canvas.mouse.x
        dragged.y = canvas.mouse.y
    if not canvas.mouse.pressed: 
        dragged = None
    elif not dragged:
        for p in s.particles:
            if abs(canvas.mouse.x-p.x) < p.radius and \
               abs(canvas.mouse.y-p.y) < p.radius:
                dragged = p

canvas.size = 500, 500
canvas.run(draw)