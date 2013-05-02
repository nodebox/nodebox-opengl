# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.insert(0, os.path.join("..",".."))

from nodebox.graphics import *
from nodebox.sound    import PD
from math             import sin, pow

# An evolutionary melody.
# The audio tones are generated in Pd, based on data sent from the canvas.

# If you open the patch manually in Pd, set start=False.
pd = PD("03-sequencer.pd", start=True)

# Selection of piano keys to play (e.g. only black keys):
PIANO = [34, 36, 38, 41, 43, 46, 48, 50]

class Note:
    
    def __init__(self, x, y):
        """ One of eight piano keys played in a sequencer.
            It regenerates after a certain amount of time to obtain variations in the melody.
        """
        self.key  = choice(PIANO)
        self.x    = x
        self.y    = y
        self.dy   = 0              # Vertical offset, changes according to time.
        self.dt   = random()       # Time step, higher = note is repeated faster.
        self.time = 0              # Increases with dt each update.
        self.life = 0              # Higher than 10 = reset note.
        self.play = random(10, 50) # Note is played when this far or less from the center.
        
    @property
    def played(self):
        return self.dy < self.play
    
    @property
    def tone(self):
        if self.played:
            return pow(2, (self.key-49)/12.0) * 440
        return 0
        
    def draw(self):
        fill(0,1,0) if self.played else fill(1)
        nostroke()
        rect(self.x, self.y + self.dy, 40, 40)
        rect(self.x, self.y - self.dy, 40, 40)
        
    def update(self):
        self.time += self.dt
        self.dy += float(self.key * sin(self.time/3.0)) / 5.0
        if self.dy < 0:
            self.life += 1
        if self.life > 10:
            self.__init__(self.x, self.y)
         
class Signal(list):

    def update(self, dy=0):
        self.append(dy)
        if len(self) > 100:
            del(self[0])
        
    def draw(self):
        """ Draws the signal wave.
            Note that only the first index gets send from Pd. 
            To achieve a more streamlined wave you would have to send the whole array.
        """
        push()
        translate(0, canvas.height/2)
        stroke(0,1,0)
        dx = float(canvas.width) / 100
        for i, dy in enumerate(self):
            dy0 = self[i-1]
            line(i*dx, dy, (i-1)*dx, dy0)
        pop()
        
melody = [Note(120+i*50, canvas.height/2) for i in range(8)]
signal = Signal()
               
def draw(canvas):
    background(0)
    data = pd.get("/metro")
    if data:
        signal.update(100.0 * data[0])
        signal.draw()
    for note in melody:
        note.update()
        note.draw()
    pd.send([note.tone for note in melody], "/input")

def stop(canvas):
    pd.stop()
    
canvas.size = 600, 450
canvas.fps = 30
canvas.run(draw, stop=stop)
