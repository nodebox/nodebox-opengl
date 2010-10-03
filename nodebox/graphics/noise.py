from random import random
from math   import floor

class PerlinNoise:
    
    def __init__(self, permutation=None):
        """ Initializes a Perlin noise generator with the given permutation pattern,
            which is a list of 256 integers between 0-255.
        """
        if not permutation:
            permutation = [random()*256 for i in range(256)]
        self._init([int(x) for x in permutation] * 2)
    
    def _init(self, p):
        self._p = p
    def _fade(self, t): 
        return t * t * t * (t * (t * 6 - 15) + 10)
    def _lerp(self, t, a, b): 
        return a + t * (b - a)
    def _grad(self, hash, x, y, z):
        u, v, h = x, y, hash & 15 
        if h >= 8: u = y
        if h >= 4:
            v = x
            if h != 12 and h != 14: v = z
        if (h&1) != 0: u = -u
        if (h&2) != 0: v = -v
        return u + v
    
    def generate(self, x, y=0, z=0):
        """ Returns a smooth value between -1.0 and 1.0.
            The x, y, z parameters determine the coordinates in the noise landscape. 
            Since the landscape is infinite, the actual value of a coordinate doesn't matter, 
            only the distance between successive steps. 
            The smaller the difference between steps, the smoother the noise sequence. 
            Steps between 0.005 and 0.1 usually work best.
        """
        lerp, grad, fade, p = self._lerp, self._grad, self._fade, self._p
        # Find unit cuve that contains point (x,y,z).
        X = int(floor(x)) & 255
        Y = int(floor(y)) & 255
        Z = int(floor(z)) & 255
        # Find relative (x,y,z) of point in cube.
        # Compute fade curves.
        x, y, z = x-floor(x), y-floor(y), z-floor(z)
        u, v, w = fade(x), fade(y), fade(z)
        # Hash coordinates of the cube corners.
        A = Y + p[X]
        B = Y + p[X+1]
        AA, AB, BA, BB = Z+p[A], Z+p[A+1], Z+p[B], Z+p[B+1]
        # Add blended results from the cube corners.
        return lerp(w, 
            lerp(v, lerp(u, grad(p[AA  ], x  , y  , z  ), 
                            grad(p[BA  ], x-1, y  , z  )),
                    lerp(u, grad(p[AB  ], x  , y-1, z  ), 
                            grad(p[BB  ], x-1, y-1, z  ))),
            lerp(v, lerp(u, grad(p[AA+1], x  , y  , z-1), 
                            grad(p[BA+1], x-1, y  , z-1)),
                    lerp(u, grad(p[AB+1], x  , y-1, z-1), 
                            grad(p[BB+1], x-1, y-1, z-1))))

try:
    # Fast C implementations:
    from nodebox.ext.noise import init, generate
    PerlinNoise._init = init
    PerlinNoise.generate = generate
except:
    pass

_generator = PerlinNoise()
def noise(x, y=0, z=0):
    return _generator.generate(x, y, z)
