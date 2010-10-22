NodeBox for OpenGL
==================

NodeBox for OpenGL is a Python module for creating 2D interactive visuals using OpenGL. It is based on the command set of the classic NodeBox for Mac OS X (http://nodebox.net). It has support for Bezier paths, text, image filters (blur, bloom, ...), offscreen rendering, animation & motion tweening, and simple 2D physics.

REQUIREMENTS
============

This set of examples requires that you have NodeBox for OpenGL:
http://cityinabottle.org/nodebox

NodeBox is expected to be located on the same path as the examples folder.

Your video hardware needs support for OpenGL 2.0.
NodeBox may not (fully) work on older hardware. Telltale signs are:
- Using image filters only works with non-transparent images. 
- Using image filters produces no visible effect, and nodebox.graphics.shader.SUPPORTED is False.
- Using the render() or filter() command throws an OffscreenBufferError.

Older hardware may produce garbled output in the following examples (that rely on image filters):
- 05-path/05-spider.py
- 07-filter/*
- 08-physics/04-animation.py 