from nodebox.graphics import *

def draw(layer):
    fill(layer.clr)
    rect(0, 0, layer.width, layer.height)

l1 = layer(120, 40, 100, 100, origin=(0.5,1.25))
l1.name =""
l1.clr = color(1,0,0,0.75)
l1.rotate(45)
l1.scale = 1.5
# Prototype copy test.
# Bound function draw() should be bound to layer with name "red".
# The new clr property should be copied as well.
l1.bind(draw, "draw")
l1 = l1.copy(None)
l1.name = "red"
print l1.__dict__["draw"]

canvas.append(l1)

l2 = layer(50,30,100,100, origin=(0,0))
l2.name = "yellow"
l2.clr = color(1,1,0,0.5)
l2.top = choice((True,False))
l2.rotate(0)
l2.bind(draw, "draw")
l1.append(l2)

l3 = layer(30,30,100,100, origin=(0,0))
l3.name = "blue"
l3.clr = color(0,0,1)
l3.top = choice((True,False))
l3.bind(draw, "draw")
l2.append(l3)

l4 = layer(80,0,100,100, origin=(0,0))
l4.name = "pink"
l4.clr = color(1,0,0.5)
l4.top = choice((True,False))
l4.rotate(20)
l4.bind(draw, "draw")
l2.append(l4)

def canvas_draw():
    
    #canvas.clear()
    #l1.duration=0
    #l1.rotate(1)
    
    # Simple AffineTransform test.
    # A black dot should be following red layer's bottom-left corner.
    tf = l1._transform()
    x,y = tf.apply(0,0)
    fill(0)
    oval(x, y, 10, 10)
    
    # AffineTransform + ray casting test.
    # Black dots should be crawling inside yellow layer,
    # even after a complex chain of layer transformations.
    for i in range(50):
        x = random(width())
        y = random(height())
        if l2.contains(x,y,transformed=True):
            fill(0)
            ellipse(x, y, 10, 10)
            
    # layer_at() test.
    # Layers underneath other layers should not propagate.
    L = l1.layer_at(canvas.mouse.x, canvas.mouse.y, clipped=False)
    if L != None:
        print "mouse is over ", L.name
    
    #fill(0)
    #p = BezierPath()
    #p.ellipse(50,50,50,50)
    #if p.contains(canvas.mouse.x, canvas.mouse.y):
    #    print "mouse is over the black oval"
    #drawpath(p)

canvas.draw = canvas_draw
canvas.run()
