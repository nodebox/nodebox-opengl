# Add the upper directory (where the nodebox module is) to the search path.
import os, sys; sys.path.append(os.path.join("..", ".."))

from nodebox.graphics import *
from nodebox.graphics.physics import Node, Edge, Graph

# Create a graph with randomly connected nodes.
# Nodes and edges can be styled with fill, stroke, strokewidth parameters.
# Each node displays its id as a text label, stored as a Text object in Node.text.
# To hide the node label, set the text parameter to None.
g = Graph()
# Random nodes.
for i in range(50):
    g.append(Node(id=str(i+1), 
        radius = 5,
        stroke = color(1,0.5), 
          text = color(1)))
# Random edges.
for i in range(75):
    node1 = choice(g.nodes)
    node2 = choice(g.nodes)
    g.append(Edge(node1, node2, 
        length = 1.0, 
        weight = random(), 
        stroke = color(1,0.5)))

# Two handy tricks to prettify the layout:
# 1) Nodes with a higher weight (i.e. incoming traffic) appear bigger.
for node in g.nodes:
    node.radius = node.radius + node.radius*node.weight
# 2) Nodes with only one connection ("leaf" nodes) have a shorter connection.
for node in g.nodes:
    if len(node.edges) == 1:
        node.edges[0].length *= 0.1
        
g.distance         = 10   # Overall spacing between nodes.
g.layout.force     = 0.01 # Strength of the attractive & repulsive force.
g.layout.repulsion = 15   # Repulsion radius.

dragged = None
def draw(canvas):
    
    background(0.26, 0.28, 0.24)
    translate(250, 250)
    
    # With weighted=True, Node.centrality is indicated by a shadow under high-traffic nodes.
    # With directed=True, edges have an arrowhead indicating the direction of the connection.
    # This requires some extra calculations.
    g.draw(weighted=True, directed=True)
    g.update(iterations=10)
    
    # Make it interactive!
    # When the mouse is pressed, remember on which node.
    # Drag this node around when the mouse is moved.
    dx = canvas.mouse.x - 250 # Undo translate().
    dy = canvas.mouse.y - 250
    global dragged
    if canvas.mouse.pressed and not dragged:
        dragged = g.node_at(dx, dy)
    if not canvas.mouse.pressed:
        dragged = None
    if dragged:
        dragged.x = dx
        dragged.y = dy
        
canvas.size = 500, 500
canvas.run(draw)
