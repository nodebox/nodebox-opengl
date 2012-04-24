NodeBox for OpenGL
==================

NodeBox for OpenGL is a Python module for creating 2D interactive visuals using OpenGL. It is based on the command set of the classic NodeBox for Mac OS X (http://nodebox.net). It has support for Bezier paths, text, image filters (blur, bloom, ...), offscreen rendering, animation & motion tweening, and simple 2D physics. Its purpose is to implement a small game engine for "City In A Bottle" (http://cityinabottle.org).

VERSION
=======

1.7

LICENSE
=======

BSD, see LICENSE.txt for further details.

REQUIREMENTS
============

NodeBox for OpenGL is built on the excellent Pyglet module. It works on all platforms if you have Python and Pyglet installed. Note: on Mac OS 10.5, Python is already installed. On Mac OS X 10.6+ (Snow Leopard), you need to install a 32-bit version of Python (Pyglet won't work as expected with the preinstalled 64-bit version).

- Python 2.5-6 : an installer can be downloaded from http://www.python.org/download/
- Pyglet 1.4+  : an installer can be downloaded from http://www.pyglet.org/

Your video hardware needs support for OpenGL 2.0.
If this is not the case, try updating to a new driver.

INSTALLATION
============

To be able to import NodeBox in your scripts, Python needs to know where the module is located. 
There are three basic ways to accomplish this:

- Put the nodebox/ folder in the same folder as your script.
- Put the nodebox/ folder in the standard location for modules so it is available to all scripts.
  The standard location depends on your operating system, for example:
  /Library/Python/2.5/site-packages/ on Mac,
  /usr/lib/python2.5/site-packages/ on Unix,
  c:\python25\Lib\site-packages\ on Windows.
- In your script, add the location of NodeBox to sys.path, before importing it:
  >>> MODULE = '/users/tom/python/nodebox'
  >>> import sys; if MODULE not in sys.path: sys.path.append(MODULE)
  >>> import nodebox

If you get an "import pyglet" error, make sure that Pyglet is installed in site-packages/ too.

Binaries:
NodeBox contains C extensions for faster mathematics. 
These are precompiled for Mac, on other systems you need to execute "python setup.py" in nodebox/ext/ manually.
Psyco (http://psyco.sourceforge.net/) can boost performance as well (if you use a 32-bit Python).
A version precompiled for Mac is included in nodebox/ext/.

USAGE
=====

- For users coming from NodeBox for Mac OS X, or NodeBox 2: this NodeBox for OpenGL does not have a built-in code editor. You can use the IDLE editor bundled with Python. On Mac OS X, we prefer TextMate (http://macromates.com).
- From the command line, you can run a script with: python example.py (or command-R in TextMate)
- This will open an application window with the output of your script.

Here is a simple NodeBox script:

>>> from nodebox.graphics import *
>>> def draw(canvas):
>>>     canvas.clear()
>>>     translate(250, 250)
>>>     rotate(canvas.frame)
>>>     rect(x=-50, y=-50, width=100, height=100)
>>> canvas.size = 500, 500
>>> canvas.run(draw)

It imports the nodebox.graphics module with the standard set of drawing commands. It defines a draw() function and attaches it to the canvas, so that it will be drawn each animation frame. It opens the main application window with canvas.run().

DOCUMENTATION
=============

http://cityinabottle.org/nodebox

ACKNOWLEDGEMENTS
================

Authors: 
- Tom De Smedt (tom@organisms.be)
- Frederik De Bleser (frederik@burocrazy.com)

Contributing authors:
- Lieven Menschaert
- Giorgio Olivero

City In A Bottle:
- Nicolas Marinus
- Ludivine Lechat
- Tim Vets
- Frederik De Bleser
- Tom De Smedt

Copyright (c) 2008 City In A Bottle
