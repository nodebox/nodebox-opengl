# Live coding example.
# See 04-live1.py.
# The commands below are read and executed in a canvas there.
# If you edit and save this file, changes are automatically reflected,
# while the canvas started in 04-live1.py keeps on running.

#canvas.clear()
for i in range(10):
    x = random(canvas.width)
    y = random(canvas.height)
    r = random(20) + 50
    fill(random(), 0.0, random(0.25), random(0.25))
    stroke(0, 0.2)
    ellipse(x, y, r, r)
