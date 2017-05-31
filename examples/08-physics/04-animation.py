from nodeboxgl.graphics import *
from nodeboxgl.graphics.physics import Particle, Force, System

# This example demonstrates the Animation object,
# which can be used to store and replay a sequence of image frames.
# This is useful for caching pre-rendered effects, like a spell or an explosion.

# This is just the explosion system from the previous example in a more condensed form.
s = System(gravity=(0, 1.0))
for i in range(80):
    s.append(Particle(x=200, y=250, mass=random(5.0,10.0), radius=5, life=30))
s.force(strength=4.5, threshold=70)

# Instead of drawing the system directly to the canvas,
# we render each step offscreen as an image,
# and then gather the images in an animation loop.
explosion = Animation(duration=0.75, loop=False)
for i in range(30):
    s.update(limit=20)
    img = render(s.draw, 400, 400)
    explosion.append(img)

# This can take several seconds:
# - calculating forces in the system is costly (if possible, load Psyco to speed them up),
# - rendering each image takes time (specifically, initialising a new empty image).
#   If possible, reduce the image frames in size (smaller images = faster rendering).

# When the user clicks on the canvas, the explosion animation is played.
# We keep a list of explosions currently playing:
explosions = []

def on_mouse_press(canvas, mouse):
    # When the mouse is clicked, start a new explosion at the mouse position.
    explosions.append((mouse.x, mouse.y, explosion.copy()))

def draw(canvas):
    
    canvas.clear()
    
    global explosions
    for x, y, e in explosions:
        push()
        translate(x-200, y-250) # Draw from the origin of the explosion.
        e.update()              # Move to the next frame in the animation.
        image(e.frame)          # Draw the current frame.
        pop()
    
    # Remove explosions that are done playing.
    explosions = [(x, y, e) for x, y, e in explosions if not e.done]

canvas.size = 700, 700
canvas.on_mouse_press = on_mouse_press # Register mouse event handler.
canvas.run(draw)
