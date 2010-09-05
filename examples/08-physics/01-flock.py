# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *
from nodebox.graphics.physics import Vector, Boid, Flock, Obstacle

# Flocking can be used to simulate birds, herds, or school of fish.
# Each "boid" in the flock adheres to a simple set of rules:
# - separation: steer to avoid crowding local flockmates,
# - alignment: steer towards the average heading of local flockmates,
# - cohesion: steer to move toward the average position of local flockmates.

# Create a new flock.
flock = Flock(30, x=50, y=50, width=500, height=500, depth=100.0)
flock.space(30) # Set the space for each boid (influences boid separation forces).
flock.sight(70) # Set the line-of-sight for each boid 
                # (influences boid cohesion and alignment forces).

# Add some obstacles that the flock will need to evade.
for i in range(3):
    o = Obstacle(x=random(50,500), y=random(50,500), radius=random(10,70))
    flock.obstacles.append(o)

def draw(canvas):

    # Clear the previous frame.
    # For fun, comment this out and observe the interesting flocking patterns.
    canvas.clear()
    
    # If the mouse is moved inside the flocking area, 
    # set it as a target for the boids.
    if flock.x < canvas.mouse.x < flock.x + flock.width and \
       flock.y < canvas.mouse.y < flock.y + flock.height:
        v = Vector(canvas.mouse.x, canvas.mouse.y, 0)
        flock.seek(v)
    else:
        flock.seek(None)
    
    # There is a random chance the flock will scatter.
    # The gather parameter here is the chance that the flock will automatically reassemble.
    if random() > 0.99995:
        flock.scatter(gather=0.05)

    # Update the flock.
    # Change the settings to observe different flocking behavior.
    flock.update(
        separation = 0.2,   # Force that keeps boids apart.
          cohesion = 0.2,   # Force that keeps boids closer together.
         alignment = 0.6,   # Force that makes boids move in the same direction.
         avoidance = 0.6,   # force that steers the boid away from obstacles.
            target = 0.2,   # Force that steers the boid towards a target vector.
             limit = 15.0,  # Maximum velocity.
         constrain = 1.0,   # Enforce bounds of flocking area.
          teleport = False) # When True, boids that cross a 2D edge teleport to the opposite side.

    # Draw the flocking area.
    # Boids can move beyond the edges, but will then steer to get back inside.
    nofill()
    stroke(0)
    strokewidth(1)
    rect(flock.x, flock.y, flock.width, flock.height)
    
    # Draw the obstacles.
    for o in flock.obstacles:
        ellipse(o.x, o.y, o.radius*2, o.radius*2)
    
    # Draw the boids.
    nostroke()
    fill(0, 0.85)
    for boid in flock:
        push()
        translate(boid.x, boid.y)
        scale(0.5 + boid.depth) # Depth is a relative number from 0.0 to 1.0.
        rotate(boid.heading)    # Heading is the direction/angle in degrees.
        arrow(0, 0, 15)
        pop()

canvas.fps = 30
canvas.size = 600, 600
canvas.run(draw)