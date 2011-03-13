#=== NODEBOX FOR OPENGL ==============================================================================

# NodeBox for OpenGL is a Python module for creating 2D interactive visuals using OpenGL. 
# It is based on the command set of the classic NodeBox for Mac OS X (http://nodebox.net). 
# It has support for Bezier paths, text, image filters (blur, bloom, ...), offscreen rendering, 
# animation & motion tweening, and simple 2D physics.

__author__    = "Tom De Smedt, Frederik De Bleser"
__version__   = "1.6"
__copyright__ = "Copyright (c) 2008-2010 City In A Bottle (cityinabottle.org)"
__license__   = "BSD"

try: import psyco; psyco.profile()
except:
    try: from ext import psyco; psyco.profile()
    except:
        pass
    
import nodebox