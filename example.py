from nodebox.graphics import *

#import psyco
#psyco.full()

size(700, 700)

from math import sin, cos, tan, log10
from random import seed

def setup():
    global a,b,buff, FRAME
    a = 10.0
    b = 0.0
    buff=None
    FRAME = 0

def draw():
    global FRAME
    FRAME += 1
    seed(0)
    canvas.clear()
    fill(0.085,0,0.05, 1)
    rect(0,0,width(),height())
    #fullscreen(True)
    global a,b,buff
    
    if buff:
        push()
        translate(width()/2, height()/2)
        rotate(FRAME/10.0)
        scale(abs(sin(FRAME/50.0)))
        translate(-width()/2, -height()/2)
        image(buff, 0, 0, alpha=0.8)
        pop()

    ### This is just the wishyworm from NodeBox
    cX = a
    cY = b
    fill(1)
    x = 180
    y = -27
    fontsize(54)
    c = 0.0
    for i in range(300):
        x += cos(cY)*15
        y += log10(cX)*8.36 + sin(cX) * 20
        fill(0.8+sin(a+c), 0.5, 0.4, 0.5)
        s = 32 + cos(cX)*17
        oval(x-s/2, y-s/2, s, s)
        cX += random(0.25)
        cY += random(0.25)
        c += 0.1
    a += 0.1
    b += 0.05
    text("hello", 20, 20, fill=color(0,0,0))
    translate(200, 200)
    ###

    buff = screenshot()    

l = Layer()
#l.draw = draw

def key_pressed(keycode, modifiers):
    print keycode, key(keycode), modifiers&SHIFT
    if keycode == KEYCODE.ESCAPE:
        canvas.done = True

#canvas.fps = 100
canvas.setup = setup
canvas.draw = draw
canvas.key_pressed = key_pressed
run()

#from context import profile
#profile()
