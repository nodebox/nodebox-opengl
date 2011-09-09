#=== PHYSICS =========================================================================================
# 2D physics functions.
# Authors: Tom De Smedt, Giorgio Olivero (Vector class)
# License: BSD (see LICENSE.txt for details).
# Copyright (c) 2008 City In A Bottle (cityinabottle.org)
# http://cityinabottle.org/nodebox

# This module can benefit greatly from loading psyco.

from math     import sqrt, pow
from math     import sin, cos, atan2, degrees, radians, pi
from random   import random
from heapq    import heappush, heappop
from warnings import warn

# float("inf") doesn't work on windows.
INFINITE = 1e20

# This module is standalone, line(), ellipse() and Text.draw() 
# must be either implemented or patched:
def line(x1, y1, x2, y2, stroke=(0,0,0,1), strokewidth=1):
    pass
def ellipse(x, y, width, height, fill=(0,0,0,1), stroke=None, strokewidth=1):
    pass

class Text:
    def __init__(self, string, **kwargs):
        self.string = string
        self.__dict__.update(kwargs)
    def copy(self):
        k = self.__dict__.copy()
        k.pop("string")
        return Text(self.string, **k)
    def draw(self):
        pass

#=====================================================================================================

#--- VECTOR ------------------------------------------------------------------------------------------
# A Euclidean vector (sometimes called a geometric or spatial vector, or - as here - simply a vector) 
# is a geometric object that has both a magnitude (or length) and direction. 
# A vector is frequently represented by a line segment with an arrow.

class Vector(object):
    
    def __init__(self, x=0, y=0, z=0, length=None, angle=None):
        """ A vector represents a direction and a magnitude (or length).
            Vectors can be added, subtracted, multiplied, divided, flipped, and 2D rotated.
            Vectors are used in physics to represent velocity and acceleration.
        """
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        if length is not None: 
            self.length = length
        if angle is not None: 
            self.angle = angle

    def copy(self):
        return Vector(self.x, self.y, self.z)
        
    def __getitem__(self, i):
        return (self.x, self.y, self.z)[i]
    def __setitem__(self, i, v):
        setattr(self, ("x", "y", "z")[i], float(v))
            
    def _get_xyz(self):
        return (self.x, self.y, self.z)
    def _set_xyz(self, (x,y,z)):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
    xyz = property(_get_xyz, _set_xyz)
        
    def _get_xy(self):
        return (self.x, self.y)
    def _set_xy(self, (x,y)):
        self.x = float(x)
        self.y = float(y)
    xy = property(_get_xy, _set_xy)

    def _get_length(self):
        return sqrt(self.x**2 + self.y**2 + self.z**2)
    def _set_length(self, n):
        d = self.length or 1
        self.x *= n/d
        self.y *= n/d
        self.z *= n/d
    length = magnitude = property(_get_length, _set_length)

    def distance(self, v):
        """ Returns the distance between two vectors,
            e.g. if two vectors would be two sides of a triangle, returns the third side.
        """
        dx = v.x - self.x
        dy = v.y - self.y
        dz = v.z - self.z
        return sqrt(dx**2 + dy**2 + dz**2)

    def distance2(self, v):
        # Squared distance, avoiding the costly root calculation.
        return (v.x-self.x)**2 + (v.y-self.y)**2 + (v.z-self.z)**2

    def normalize(self):
        """ Normalizes the vector to a unit vector with length=1.
        """
        d = self.length or 1
        self.x /= d
        self.y /= d
        self.z /= d

    def _normalized(self):
        """ Yields a new vector that is the normalized vector of this vector.
        """
        d = self.length
        if d == 0: 
            return self.copy()
        return Vector(self.x/d, self.y/d, self.z/d)
    normalized = unit = property(_normalized)

    def reverse(self):
        """ Reverses the direction of the vector so it points in the opposite direction.
        """
        self.x = -self.x
        self.y = -self.y
        self.z = -self.z
    flip = reverse

    def _reversed(self):
        """ Yields a new vector pointing in the opposite direction of this vector.
        """
        return Vector(-self.x, -self.y, -self.z)
    reversed = flipped = inverse = property(_reversed)

    # v.normal, v.angle, v.rotate(), v.rotated() and v.angle_to() are defined in 2D.
    # v.in2D.rotate() is here for decorational purposes.
    @property
    def in2D(self):
        return self

    def _orthogonal(self):
        """ Yields a new vector whose 2D angle is 90 degrees (perpendicular) to this vector.
            In 3D, there would be many perpendicular vectors.
        """
        return Vector(self.y, -self.x, self.z)
    orthogonal = perpendicular = normal = property(_orthogonal)
    
    def _get_angle(self):
        """ Yields the 2D direction of the vector.
        """
        return degrees(atan2(self.y, self.x))
    def _set_angle(self, degrees):
        d = self.length
        self.x = cos(radians(degrees)) * d
        self.y = sin(radians(degrees)) * d
    angle = direction = property(_get_angle, _set_angle)

    def rotate(self, degrees):
        """ Rotates the direction of the vector in 2D.
        """
        self.angle += degrees
        
    def rotated(self, degrees):
        """ Returns a copy of the vector with direction rotated in 2D.
        """
        v = self.copy()
        v.rotate(degrees)
        return v

    def angle_to(self, v):
        """ Returns the 2D angle between two vectors.
        """
        return degrees(atan2(v.y, v.x) - atan2(self.y, self.x))
    angle_between = angle_to
    
    # Arithmetic operators.
    # + - * / returns new vector objects.
    def __add__(self, v):
        if isinstance(v, (int, float)): 
            return Vector(self.x+v, self.y+v, self.z+v)
        return Vector(self.x+v.x, self.y+v.y, self.z+v.z)
    def __sub__(self, v):
        if isinstance(v, (int, float)): 
            return Vector(self.x-v, self.y-v, self.z-v)
        return Vector(self.x-v.x, self.y-v.y, self.z-v.z)
    def __mul__(self, v):
        if isinstance(v, (int, float)): 
            return Vector(self.x*v, self.y*v, self.z*v)
        return Vector(self.x*v.x, self.y*v.y, self.z*v.z)
    def __div__(self, v):
        if isinstance(v, (int, float)): 
            return Vector(self.x/v, self.y/v, self.z/v)
        return Vector(self.x/v.x, self.y/v.y, self.z/v.z)
    
    # += -= *= /= modify the vector coordinates in-place.
    def __iadd__(self, v):
        if isinstance(v, (int, float)):
            self.x+=v; self.y+=v; self.z+=v; return self
        self.x+=v.x; self.y+=v.y; self.z+=v.z; return self
    def __isub__(self, v):
        if isinstance(v, (int, float)):
            self.x-=v; self.y-=v; self.z-=v; return self
        self.x-=v.x; self.y-=v.y; self.z-=v.z; return self
    def __imul__(self, v):
        if isinstance(v, (int, float)):
            self.x*=v; self.y*=v; self.z*=v; return self
        self.x*=v.x; self.y*=v.y; self.z*=v.z; return self
    def __idiv__(self, v):
        if isinstance(v, (int, float)):
            self.x/=v; self.y/=v; self.z/=v; return self
        self.x/=v.x; self.y/=v.y; self.z/=v.z; return self

    def dot(self, v):
        """ Returns a scalar that is the dot product between the two vectors.
        """
        return self.x*v.x + self.y*v.y + self.z*v.z
        
    def cross(self, v):
        """ Returns a new vector that is the cross product between the two vectors.
        """
        return Vector(self.y*v.z - self.z*v.y, 
                      self.z*v.x - self.x*v.z, 
                      self.x*v.y - self.y*v.x)

    def __neg__(self):
		return Vector(-self.x, -self.y, -self.z)

    def __eq__(self, v):
        return isinstance(v, Vector) and self.x == v.x and self.y == v.y and self.z == v.z
    def __ne__(self, v):
        return not self.__eq__(v)

    def __repr__(self): 
        return "%s(%.2f, %.2f, %.2f)" % (self.__class__.__name__, self.x, self.y, self.z)

    def draw(self, x, y):
        """ Draws the vector in 2D (z-axis is ignored). 
            Set stroke() and strokewidth() first.
        """
        ellipse(x, y, 4, 4)
        line(x, y, x+self.x, y+self.y)

#=====================================================================================================

#--- FLOCKING ----------------------------------------------------------------------------------------
# Boids is an artificial life program, developed by Craig Reynolds in 1986, 
# which simulates the flocking behavior of birds.
# Boids is an example of emergent behavior, the complexity of Boids arises 
# from the interaction of individual agents adhering to a set of simple rules:
# - separation: steer to avoid crowding local flockmates,
# - alignment: steer towards the average heading of local flockmates,
# - cohesion: steer to move toward the average position of local flockmates.
# Unexpected behavior, such as splitting flocks and reuniting after avoiding obstacles, 
# can be considered emergent. The boids framework is often used in computer graphics, 
# providing realistic-looking representations of flocks of birds and other creatures, 
# such as schools of fish or herds of animals.

_UID = 0
def _uid():
    global _UID; _UID+=1; return _UID

class Boid:
    
    def __init__(self, flock, x=0, y=0, z=0, sight=70, space=30):
        """ An agent in a flock with an (x,y,z)-position subject to different forces.
            - sight : radius of local flockmates when calculating cohesion and alignment.
            - space : radius of personal space when calculating separation.
        """
        self._id      = _uid()
        self.flock    = flock
        self.x        = x
        self.y        = y
        self.z        = z
        self.velocity = Vector(random()*2-1, random()*2-1, random()*2-1)
        self.target   = None  # A target Vector towards which the boid will steer.
        self.sight    = sight # The radius of cohesion and alignment, and visible obstacles.
        self.space    = space # The radius of separation.
        self.dodge    = False # Avoiding an obstacle?
        self.crowd    = 0     # Percentage (0.0-1.0) of flockmates within sight.
    
    def __eq__(self, other):
        # Comparing boids by id makes it significantly faster.
        return isinstance(other, Boid) and self._id == other._id
    def __ne__(self, other):
        return not self.__eq__(other)
                
    def copy(self):
        b = Boid(self.flock, self.x, self.y, self.z, self.sight, self.space)
        b.velocity = self.velocity.copy()
        b.target   = self.target
        return b
        
    @property
    def heading(self):
        """ The boid's heading as an angle in degrees.
        """
        return self.velocity.angle
        
    @property
    def depth(self):
        """ The boid's relative depth (0.0-1.0) in the flock's container box.
        """
        return not self.flock.depth and 1.0 or max(0.0, min(1.0, self.z / self.flock.depth))
    
    def near(self, boid, distance=50):
        """ Returns True if the given boid is within distance.
        """
        # Distance is measured in a box instead of a sphere for performance.
        return abs(self.x - boid.x) < distance and \
               abs(self.y - boid.y) < distance and \
               abs(self.z - boid.z) < distance
    
    def separation(self, distance=25):
        """ Returns steering velocity (vx,vy,vz) to avoid crowding local flockmates.
        """
        vx = vy = vz = 0.0
        for b in self.flock:
            if b != self:
                if abs(self.x-b.x) < distance: vx += self.x - b.x
                if abs(self.y-b.y) < distance: vy += self.y - b.y
                if abs(self.z-b.z) < distance: vz += self.z - b.z
        return vx, vy, vz
        
    def alignment(self, distance=50):
        """ Returns steering velocity (vx,vy,vz) towards the average heading of local flockmates.
        """
        vx = vy = vz = n = 0.0
        for b in self.flock:
            if b != self and b.near(self, distance):
                vx += b.velocity.x
                vy += b.velocity.y
                vz += b.velocity.z; n += 1
        if n: 
            return (vx/n-self.velocity.x), (vy/n-self.velocity.y), (vz/n-self.velocity.z)
        return vx, vy, vz

    def cohesion(self, distance=40):
        """ Returns steering velocity (vx,vy,vz) towards the average position of local flockmates.
        """
        vx = vy = vz = n = 0.0
        for b in self.flock:
            if b != self and b.near(self, distance):
                vx += b.x
                vy += b.y 
                vz += b.z; n += 1
        # Calculate percentage of flockmates within sight.
        self.crowd = float(n) / (len(self.flock) or 1)
        if n: 
            return (vx/n-self.x), (vy/n-self.y), (vz/n-self.z)
        return vx, vy, vz

    def avoidance(self):
        """ Returns steering velocity (vx,vy,0) to avoid 2D obstacles.
            The boid is not guaranteed to avoid collision.
        """
        vx = vy = 0.0
        self.dodge = False
        for o in self.flock.obstacles:
            dx = o.x - self.x
            dy = o.y - self.y
            d = sqrt(dx**2 + dy**2)     # Distance to obstacle.
            s = (self.sight + o.radius) # Visibility range.
            if d < s:
                self.dodge = True
                # Force grows exponentially from 0.0 to 1.0, 
                # where 1.0 means the boid touches the obstacle circumference.
                f = (d-o.radius) / (s-o.radius)
                f = (1-f)**2
                if d < o.radius:
                    f *= 4
                    #self.velocity.reverse()
                vx -= dx * f
                vy -= dy * f
        return (vx, vy, 0)
        
    def limit(self, speed=10.0):
        """ Limits the boid's velocity (the boid can momentarily go very fast).
        """
        v = self.velocity
        m = max(abs(v.x), abs(v.y), abs(v.z)) or 1
        if abs(v.x) > speed: v.x = v.x / m * speed
        if abs(v.y) > speed: v.y = v.y / m * speed
        if abs(v.z) > speed: v.z = v.z / m * speed
    
    def update(self, separation=0.2, cohesion=0.2, alignment=0.6, avoidance=0.6, target=0.2, limit=15.0):
        """ Updates the boid's velocity based on the cohesion, separation and alignment forces.
            - separation: force that keeps boids apart.
            - cohesion  : force that keeps boids closer together.
            - alignment : force that makes boids move in the same direction.
            - avoidance : force that steers the boid away from obstacles.
            - target    : force that steers the boid towards a target vector.
            - limit     : maximum velocity.
        """
        f = 0.1
        m1, m2, m3, m4, m5 = separation*f, cohesion*f, alignment*f, avoidance*f, target*f
        vx1, vy1, vz1 = self.separation(self.space)
        vx2, vy2, vz2 = self.cohesion(self.sight)
        vx3, vy3, vz3 = self.alignment(self.sight)
        vx4, vy4, vz4 = self.avoidance()
        vx5, vy5, vz5 = self.target and (
            (self.target.x-self.x), 
            (self.target.y-self.y), 
            (self.target.z-self.z)) or (0,0,0)
        self.velocity.x += m1*vx1 + m2*vx2 + m3*vx3 + m4*vx4 + m5*vx5
        self.velocity.y += m1*vy1 + m2*vy2 + m3*vy3 + m4*vy4 + m5*vy5
        self.velocity.z += m1*vz1 + m2*vz2 + m3*vz3 + m4*vz4 + m5*vz5
        self.velocity.z  = self.flock.depth and self.velocity.z or 0 # No z-axis for Flock.depth=0 
        self.limit(speed=limit)
        self.x += self.velocity.x
        self.y += self.velocity.y
        self.z += self.velocity.z
 
    def seek(self, vector):
        """ Sets the given Vector as the boid's target.
        """
        self.target = vector
        
    def __repr__(self):
        return "Boid(x=%.1f, y=%.1f, z=%.1f)" % (self.x, self.y, self.z)

class Obstacle:
    
    def __init__(self, x=0, y=0, z=0, radius=10):
        """ An obstacle with an (x, y, z) position and a radius.
            Boids will steer around obstacles that the flock is aware of, and that they can see.
        """
        self.x = x
        self.y = y
        self.z = z
        self.radius = radius
        
    def copy(self):
        return Obstacle(self.x, self.y, self.z, self.radius)

    def __repr__(self):
        return "Obstacle(x=%.1f, y=%.1f, z=%.1f, radius=%.1f)" % (self.x, self.y, self.z, self.radius)

class Flock(list):
    
    def __init__(self, amount, x, y, width, height, depth=100.0, obstacles=[]):
        """ A flock of the given amount of boids, confined to a box.
            Obstacles can be added to Flock.obstacles (boids will steer away from them).
        """
        self.x         = x
        self.y         = y
        self.width     = width
        self.height    = height
        self.depth     = depth
        self.scattered = False
        self.gather    = 0.05
        self.obstacles = []
        for i in range(amount):
            # Boids will originate from the center of the flocking area.
            b = Boid(self, 
                self.x + 0.5 * (width  or 0), 
                self.y + 0.5 * (height or 0), 
                         0.5 * (depth  or 0))
            self.append(b)
    
    @property
    def boids(self):
        return self
    
    def copy(self):
        f = Flock(0, self.x, self.y, self.width, self.height, self.depth)        
        f.scattered = self.scattered
        f.gather    = self.gather
        f.obstacles = [o.copy() for o in self.obstacles]
        for b in self:
            f.append(b.copy())
        return f

    def seek(self, target):
        """ Sets the target vector of all boids in the flock (None for no target).
        """
        for b in self: 
            b.seek(target)

    def sight(self, distance):
        for b in self: 
            b.sight = distance
            
    def space(self, distance):
        for b in self: 
            b.space = distance
    
    def constrain(self, force=1.0, teleport=False):
        """ Keep the flock inside the rectangular flocking area.
            The given force determines how fast the boids will swivel when near an edge.
            Alternatively, with teleport=True boids that cross a 2D edge teleport to the opposite side.
        """
        f = 5
        def _teleport(b):
            if b.x < self.x:
                b.x = self.x + self.width
            if b.x > self.x + self.width: 
                b.x = self.x
            if b.y < self.y: 
                b.y = self.y + self.height
            if b.y > self.y + self.height:
                b.y = self.y
        def _constrain(b):
            if b.x < self.x:
                b.velocity.x += force * f * random()
            if b.x > self.x + self.width: 
                b.velocity.x -= force * f * random()
            if b.y < self.y: 
                b.velocity.y += force * f * random()
            if b.y > self.y + self.height:
                b.velocity.y -= force * f * random()
        for b in self:
            if b.z < 0: 
                b.velocity.z += force * f * random()
            if b.z > self.depth: 
                b.velocity.z -= force * f * random()
            teleport and _teleport(b) \
                      or _constrain(b)

    def scatter(self, gather=0.05):
        """ Scatters the flock, until Flock.scattered=False.
            Flock.gather is the chance (0.0-1.0, or True/False) that the flock will reunite by itself.
        """
        self.scattered = True
        self.gather = gather

    def update(self, separation=0.2, cohesion=0.2, alignment=0.6, avoidance=0.6, target=0.2, limit=15.0, constrain=1.0, teleport=False):
        """ Updates the boid velocities based on the given forces.
            Different forces elicit different flocking behavior; fine-tuning them can be delicate.
        """
        if self.scattered:
            # When scattered, make the boid cohesion negative and diminish alignment.
            self.scattered = (random() > self.gather)
            cohesion = -0.01
            alignment *= 0.25
        for b in self:
            b.update(separation, cohesion, alignment, avoidance, target, limit)
        self.constrain(force=constrain, teleport=teleport)

    def by_depth(self):
        """ Returns the boids in the flock sorted by depth (z-axis).
        """
        return sorted(self, key=lambda boid: boid.z)

    def __repr__(self):
        return "Flock(%s)" % repr(list(self))

flock = Flock

#=== SYSTEM ==========================================================================================
# A computer graphics technique to simulate certain fuzzy phenomena, 
# which are otherwise very hard to reproduce with conventional rendering techniques: 
# fire, explosions, smoke, moving water, sparks, falling leaves, clouds, fog, snow, dust, 
# meteor tails, hair, fur, grass, or abstract visual effects like glowing trails, magic spells.

#--- FORCE -------------------------------------------------------------------------------------------

class Force:
    
    def __init__(self, particle1, particle2, strength=1.0, threshold=100.0):
        """ An attractive or repulsive force that causes objects with a mass to accelerate.
            A negative strength indicates an attractive force.
        """
        self.particle1 = particle1
        self.particle2 = particle2
        self.strength  = strength
        self.threshold = threshold
                
    def apply(self):
        """ Applies the force between two particles, based on the distance and mass of the particles.
        """
        # Distance has a minimum threshold to keep forces from growing too large,
        # e.g. distance 100 divides force by 10000, distance 5 only by 25.
        # Decreasing the threshold moves particles that are very close to each other away faster.
        dx = self.particle2.x - self.particle1.x
        dy = self.particle2.y - self.particle1.y
        d = sqrt(dx*dx + dy*dy)
        d = max(d, self.threshold)
        # The force between particles increases according to their weight.
        # The force decreases as distance between them increases.
        f = 10.0 * -self.strength * self.particle1.mass * self.particle2.mass
        f = f / (d*d)
        fx = f * dx / d
        fy = f * dy / d
        self.particle1.force.x += fx
        self.particle1.force.y += fy
        self.particle2.force.x -= fx
        self.particle2.force.y -= fy

    def __repr__(self):
        return "Force(strength=%.2f)" % self.strength

force = Force

#--- SPRING ------------------------------------------------------------------------------------------

class Spring:
    
    def __init__(self, particle1, particle2, length, strength=1.0):
        """ A force that exerts attractive resistance when its length changes.
            A spring acts as a flexible (but secure) connection between two particles.
        """
        self.particle1 = particle1
        self.particle2 = particle2
        self.strength  = strength
        self.length    = length
        self.snapped   = False
    
    def snap(self):
        """ Breaks the connection between the two particles.
        """
        self.snapped = True
    
    def apply(self):
        """ Applies the force between two particles.
        """
        # Distance between two particles.
        dx = self.particle2.x - self.particle1.x
        dy = self.particle2.y - self.particle1.y
        d = sqrt(dx*dx + dy*dy)
        if d == 0: 
            return
        # The attractive strength decreases for heavy particles.
        # The attractive strength increases when the spring is stretched.
        f = 10.0 * self.strength / (self.particle1.mass * self.particle2.mass)
        f = f * (d - self.length)
        fx = f * dx / d
        fy = f * dy / d
        self.particle1.force.x += fx
        self.particle1.force.y += fy
        self.particle2.force.x -= fx
        self.particle2.force.y -= fy
        
    def draw(self, **kwargs):
        line(self.particle1.x, self.particle1.y, 
             self.particle2.x, self.particle2.y, **kwargs)

    def __repr__(self):
        return "Spring(strength='%.2f', length='%.2f')" % (self.strength, self.length)

spring = Spring

#--- PARTICLE ----------------------------------------------------------------------------------------

MASS = "mass"

class Particle:
    
    def __init__(self, x, y, velocity=(0.0,0.0), mass=10.0, radius=10.0, life=None, fixed=False):
        """ An object with a mass subjected to attractive and repulsive forces.
            The object's velocity is an inherent force (e.g. a rocket propeller to escape gravity).
        """
        self._id      = _uid()
        self.x        = x + random()
        self.y        = y + random()
        self.mass     = mass
        self.radius   = radius == MASS and mass or radius
        self.velocity = isinstance(velocity, tuple) and Vector(*velocity) or velocity
        self.force    = Vector(0.0, 0.0) # Force accumulator.
        self.life     = life
        self._age     = 0.0
        self.dead     = False
        self.fixed    = fixed
    
    @property
    def age(self):
        # Yields the particle's age as a number between 0.0 and 1.0.
        return self.life and min(1.0, float(self._age) / self.life) or 0.0
    
    def draw(self, **kwargs):
        r = self.radius * (1 - self.age)
        ellipse(self.x, self.y, r*2, r*2, **kwargs)
        
    def __eq__(self, other):
        return isinstance(other, Particle) and self._id == other._id
    def __ne__(self, other):
        return not self.__eq__(other)
   
    def __repr__(self):
        return "Particle(x=%.1f, y=%.1f, radius=%.1f, mass=%.1f)" % (
            self.x, self.y, self.radius, self.mass)

particle = Particle

#--- SYSTEM ------------------------------------------------------------------------------------------

class flist(list):
    
    def __init__(self, system):
        # List of forces or springs that keeps System.dynamics in synch.
        self.system = system
    
    def insert(self, i, force):
        list.insert(self, i, force)
        self.system._dynamics.setdefault(force.particle1._id, []).append(force)
        self.system._dynamics.setdefault(force.particle2._id, []).append(force)
    def append(self, force):
        self.insert(len(self), force)
    def extend(self, forces):
        for f in forces: self.append(f)

    def pop(self, i):
        f = list.pop(self, i)
        self.system._dynamics.pop(force.particle1._id)
        self.system._dynamics.pop(force.particle2._id)
        return f        
    def remove(self, force):
        i = self.index(force); self.pop(i)

class System(object):
    
    def __init__(self, gravity=(0,0), drag=0.0):
        """ A collection of particles and the forces working on them.
        """
        self.particles = []
        self.emitters  = []
        self.forces    = flist(self)
        self.springs   = flist(self)
        self.gravity   = isinstance(gravity, tuple) and Vector(*gravity) or gravity
        self.drag      = drag
        self._dynamics = {} # Particle id linked to list of applied forces.

    def __len__(self):
        return len(self.particles)
    def __iter__(self):
        return iter(self.particles)
    def __getitem__(self, i):
        return self.particles[i]

    def extend(self, x):
        for x in x: self.append(x)
    def append(self, x):
        if isinstance(x, Particle) and not x in self.particles:
            self.particles.append(x)
        elif isinstance(x, Force):
            self.forces.append(x)
        elif isinstance(x, Spring):
            self.springs.append(x)
        elif isinstance(x, Emitter):
            self.emitters.append(x)
            self.extend(x.particles)
            x.system = self

    def _cross(self, f=lambda particle1, particle2: None, source=None, particles=[]):
        # Applies function f to any two given particles in the list,
        # or between source and any other particle if source is given.
        P = particles or self.particles
        for i, p1 in enumerate(P):
            if source is None: 
                [f(p1, p2) for p2 in P[i+1:]]
            else:
                f(source, p1)

    def force(self, strength=1.0, threshold=100, source=None, particles=[]):
        """ The given force is applied between each two particles.
            The effect this yields (with a repulsive force) is an explosion.
            - source: one vs. all, apply the force to this particle with all others.
            - particles: a list of particles to apply the force to (some vs. some or some vs. source).
            Be aware that 50 particles wield yield 1250 forces: O(n**2/2); or O(n) with source.
            The force is applied to particles present in the system,
            those added later on are not subjected to the force.
        """
        f = lambda p1, p2: self.forces.append(Force(p1, p2, strength, threshold))
        self._cross(f, source, particles)
        
    def dynamics(self, particle, type=None):
        """ Returns a list of forces working on the particle, optionally filtered by type (e.g. Spring).
        """
        F = self._dynamics.get(isinstance(particle, Particle) and particle._id or particle, [])
        F = [f for f in F if type is None or isinstance(f, type)]
        return F
        
    def limit(self, particle, m=None):
        """ Limits the movement of the particle to m.
            When repulsive particles are close to each other, their force can be very high.
            This results in large movement steps, and gaps in the animation.
            This can be remedied by limiting the total force.
        """
        # The right way to do it requires 4x sqrt():
        # if m and particle.force.length > m: 
        #    particle.force.length = m
        # if m and particle.velocity.length > m: 
        #    particle.velocity.length = m
        if m is not None:
            for f in (particle.force, particle.velocity):
                if abs(f.x) > m: 
                    f.y *= m / abs(f.x)
                    f.x *= m / abs(f.x)
                if abs(f.y) > m: 
                    f.x *= m / abs(f.y)
                    f.y *= m / abs(f.y)

    def update(self, limit=30):
        """ Updates the location of the particles by applying all the forces.
        """
        for e in self.emitters:
            # Fire particles from emitters.
            e.update()
        for p in self.particles:
            # Apply gravity. Heavier objects have a stronger attraction.
            p.force.x = 0
            p.force.y = 0
            p.force.x += 0.1 *  self.gravity.x * p.mass
            p.force.y += 0.1 * -self.gravity.y * p.mass
        for f in self.forces:
            # Apply attractive and repulsive forces between particles.
            if not f.particle1.dead and \
               not f.particle2.dead:
                f.apply()
        for s in self.springs:
            # Apply spring forces between particles.
            if not s.particle1.dead and \
               not s.particle2.dead and \
               not s.snapped:
                s.apply()
        for p in self.particles:
            if not p.fixed:
                # Apply drag.
                p.velocity.x *= 1.0 - min(1.0, self.drag)
                p.velocity.y *= 1.0 - min(1.0, self.drag)
                # Apply velocity.
                p.force.x += p.velocity.x
                p.force.y += p.velocity.y
                # Limit the accumulated force and update the particle's position.
                self.limit(p, limit)
                p.x += p.force.x
                p.y += p.force.y
            if p.life:
                # Apply lifespan.
                p._age += 1
                p.dead = p._age > p.life
    
    @property
    def dead(self):
        # Yields True when all particles are dead (and we don't need to update anymore).
        for p in self.particles:
            if not p.dead: return False
        return True
    
    def draw(self, **kwargs):
        """ Draws the system at the current iteration.
        """
        for s in self.springs:
            if not s.particle1.dead and \
               not s.particle2.dead and \
               not s.snapped:
                s.draw(**kwargs)
        for p in self.particles:
            if not p.dead:
                p.draw(**kwargs)

    def __repr__(self):
        return "System(particles=%i, forces=%i, springs=%i)" % \
            (len(self.particles), len(self.forces), len(self.springs))

system = System

# Notes:
# While this system is interesting for many effects, it is unstable.
# If for example very strong springs are applied, particles will start "shaking".
# This is because the forces are simply added to the particle's position instead of integrated.
# See also:
# http://local.wasp.uwa.edu.au/~pbourke/miscellaneous/particle/
# http://local.wasp.uwa.edu.au/~pbourke/miscellaneous/particle/particlelib.c

#def euler_derive(particle, dt=0.1):
#    particle.x += particle.velocity.x * dt
#    particle.y += particle.velocity.y * dt
#    particle.velocity.x += particle.force.x / particle.mass * dt
#    particle.velocity.y += particle.force.y / particle.mass * dt

# If this is applied, springs will need a velocity dampener:
#fx = f + 0.01 + (self.particle2.velocity.x - self.particle1.velocity.x) * dx / d
#fy = f + 0.01 + (self.particle2.velocity.y - self.particle1.velocity.y) * dy / d

# In pure Python this is slow, since only 1/10 of the force is applied each System.update().

#--- EMITTER -----------------------------------------------------------------------------------------

class Emitter(object):
    
    def __init__(self, x, y, angle=0, strength=1.0, spread=10):
        """ A source that shoots particles in a given direction with a given strength.
        """
        self.system    = None   # Set when appended to System.
        self.particles = []
        self.x         = x
        self.y         = y
        self.velocity  = Vector(1, 1, length=strength, angle=angle)
        self.spread    = spread # Angle-of-view.
        self._i        = 0      # Current iteration.

    def __len__(self):
        return len(self.particles)
    def __iter__(self):
        return iter(self.particles)
    def __getitem__(self, i):
        return self.particles[i]

    def extend(self, x, life=100):
        for x in x: self.append(x, life)
    def append(self, particle, life=100):
        particle.life = particle.life or life
        particle._age = particle.life
        particle.dead = True
        self.particles.append(particle)
        if self.system is not None:
            # Also append the particle to the system the emitter is part of.
            self.system.append(particle)
    
    def _get_angle(self):
        return self.velocity.angle
    def _set_angle(self, v):
        self.velocity.angle = v
        
    angle = property(_get_angle, _set_angle)

    def _get_strength(self):
        return self.velocity.length
    def _set_strength(self, v):
        self.velocity.length = max(v, 0.01)
        
    strength = length = magnitude = property(_get_strength, _set_strength)
            
    def update(self):
        """ Update the system and respawn dead particles.
            When a particle dies, it can be reused as a new particle fired from the emitter.
            This is more efficient than creating a new Particle object.
        """
        self._i += 1 # Respawn occurs gradually.
        p = self.particles[self._i % len(self.particles)]
        if p.dead:
            p.x        = self.x
            p.y        = self.y
            p.velocity = self.velocity.rotated(self.spread * 0.5 * (random()*2-1))
            p._age     = 0
            p.dead     = False

emitter = Emitter

#=== GRAPH ===========================================================================================
# Graph visualization is a way of representing information as diagrams of abstract graphs and networks. 
# Automatic graph drawing has many important applications in software engineering, 
# database and web design, networking, and in visual interfaces for many other domains.

#--- NODE --------------------------------------------------------------------------------------------

def deepcopy(o):
    # A color can be represented as a tuple or as a nodebox.graphics.Color object,
    # in which case it needs to be copied by invoking Color.copy().
    if o is None:
        return o
    if isinstance(o, (basestring, bool, int, float, long, complex)):
        return o
    if isinstance(o, (list, tuple, set)):
        return o.__class__(deepcopy(v) for v in o)
    if isinstance(o, dict):
        return dict((deepcopy(k), deepcopy(v)) for k,v in o.iteritems())
    if hasattr(o, "copy"):
        return o.copy()
    raise Exception, "don't know how to copy %s" % o.__class__.__name__

class Node(object):
    
    def __init__(self, id="", radius=5, **kwargs):
        """ A node with a unique id in the graph.
            Node.id is drawn as a text label, unless optional parameter text=False.
            Optional parameters include: fill, stroke, strokewidth, text, font, fontsize, fontweight.
        """
        self.graph       = None
        self.links       = Links()
        self.id          = id
        self._x          = 0    # Calculated by Graph.layout.update().
        self._y          = 0    # Calculated by Graph.layout.update().
        self.force       = Vector(0,0)
        self.radius      = radius
        self.fill        = kwargs.pop("fill", None)
        self.stroke      = kwargs.pop("stroke", (0,0,0,1))
        self.strokewidth = kwargs.pop("strokewidth", 1)
        self.text        = kwargs.get("text", True) and \
            Text(unicode(id), 
                   width = 85,
                    fill = kwargs.pop("text", (0,0,0,1)), 
                fontsize = kwargs.pop("fontsize", 11), **kwargs) or None
        self.fixed       = kwargs.pop("fixed", False)
        self._weight     = None # Calculated by Graph.eigenvector_centrality().
        self._centrality = None # Calculated by Graph.betweenness_centrality().
    
    @property
    def _distance(self):
        # Graph.distance controls the (x,y) spacing between nodes.
        return self.graph and float(self.graph.distance) or 1.0
    
    def _get_x(self):
        return self._x * self._distance
    def _get_y(self):
        return self._y * self._distance
    def _set_x(self, v):
        self._x = v / self._distance
    def _set_y(self, v):
        self._y = v / self._distance

    x = property(_get_x, _set_x)
    y = property(_get_y, _set_y)

    @property
    def edges(self):
        return self.graph is not None \
           and [e for e in self.graph.edges if self.id in (e.node1, e.node2)] \
            or []
    
    @property
    def weight(self):
        if self.graph and self._weight is None:
            self.graph.eigenvector_centrality()
        return self._weight
        
    @property
    def centrality(self):
        if self.graph and self._centrality is None:
            self.graph.betweenness_centrality()
        return self._centrality
        
    def flatten(self, depth=1, _visited=None):
        """ Recursively lists the node and nodes linked to it.
            Depth 0 returns a list with the node.
            Depth 1 returns a list with the node and all the directly linked nodes.
            Depth 2 includes the linked nodes' links, and so on.
        """
        _visited = _visited or {}
        _visited[self.id] = (self, depth)
        if depth >= 1:
            for n in self.links: 
                if n.id not in _visited or _visited[n.id][1] < depth-1:
                    n.flatten(depth-1, _visited)
        return [n for n,d in _visited.values()] # Fast, but not order-preserving.
    
    def draw(self, weighted=False):
        """ Draws the node as a circle with the given radius, fill, stroke and strokewidth.
            Draws the node centrality as a shadow effect when weighted=True.
            Draws the node text label.
            Override this method in a subclass for custom drawing.
        """
        # Draw the node weight as a shadow (based on node betweenness centrality).
        if weighted is not False and self.centrality > (weighted==True and -1 or weighted):
            w = self.centrality * 35
            ellipse(
                self.x, 
                self.y, 
                self.radius*2 + w, 
                self.radius*2 + w, fill=(0,0,0,0.2), stroke=None)
        # Draw the node.
        ellipse(
            self.x, 
            self.y, 
            self.radius*2, 
            self.radius*2, fill=self.fill, stroke=self.stroke, strokewidth=self.strokewidth)
        # Draw the node text label.
        if self.text:
            self.text.draw(
                self.x + self.radius, 
                self.y + self.radius)
        
    def contains(self, x, y):
        return abs(self.x - x) < self.radius*2 and \
               abs(self.y - y) < self.radius*2
               
    def __repr__(self):
        return "%s(id=%s)" % (self.__class__.__name__, repr(self.id))

    def __eq__(self, node):
        return isinstance(node, Node) and self.id == node.id
    def __ne__(self, node):
        return not self.__eq__(node)

class Links(list):
    
    def __init__(self): 
        """ A list in which each node has an associated edge.
            The edge() method returns the edge for a given node id.
        """
        self.edges = dict()
    
    def append(self, node, edge=None):
        if node.id not in self.edges:
            list.append(self, node)
        self.edges[node.id] = edge

    def remove(self, node):
        list.remove(self, node)
        self.edges.pop(node.id, None)

    def edge(self, node): 
        return self.edges.get(isinstance(node, Node) and node.id or node)

#--- EDGE --------------------------------------------------------------------------------------------

coordinates = lambda x, y, d, a: (x + d*cos(radians(a)), y + d*sin(radians(a)))

class Edge(object):

    def __init__(self, node1, node2, weight=0.0, length=1.0, type=None, stroke=(0,0,0,1), strokewidth=1):
        """ A connection between two nodes.
            Its weight indicates the importance (not the cost) of the connection.
            Its type is useful in a semantic network (e.g. "is-a", "is-part-of", ...)
        """
        self.node1       = node1
        self.node2       = node2
        self._weight     = weight
        self.length      = length
        self.type        = type
        self.stroke      = stroke
        self.strokewidth = strokewidth
    
    def _get_weight(self): 
        return self._weight
    def _set_weight(self, v):
        self._weight = v
        # Clear cached adjacency map in the graph, since edge weights have changed.
        if self.node1.graph is not None: 
            self.node1.graph._adjacency, self.node1.graph._paths = None, {}
        if self.node2.graph is not None: 
            self.node2.graph._adjacency, self.node1.graph._paths = None, {}
    
    weight = property(_get_weight, _set_weight)
        
    def draw(self, weighted=False, directed=False):
        """ Draws the edge as a line with the given stroke and strokewidth (increased with Edge.weight).
            Override this method in a subclass for custom drawing.
        """
        w = weighted and self.weight or 0
        line(
            self.node1.x, 
            self.node1.y, 
            self.node2.x, 
            self.node2.y, stroke=self.stroke, strokewidth=self.strokewidth+w)
        if directed:
            self.draw_arrow(stroke=self.stroke, strokewidth=self.strokewidth+w)
            
    def draw_arrow(self, **kwargs):
        """ Draws the direction of the edge as an arrow on the rim of the receiving node.
        """
        x0, y0 = self.node1.x, self.node1.y
        x1, y1 = self.node2.x, self.node2.y
        # Find the edge's angle based on node1 and node2 position.
        a = degrees(atan2(y1-y0, x1-x0))
        # The arrow points to node2's rim instead of it's center.
        r = self.node2.radius
        d = sqrt(pow(x1-x0, 2) + pow(y1-y0, 2))
        x01, y01 = coordinates(x0, y0, d-r-1, a)
        # Find the two other arrow corners under the given angle.
        r = max(kwargs.get("strokewidth", 1) * 3, 6)
        dx1, dy1 = coordinates(x01, y01, -r, a-20)
        dx2, dy2 = coordinates(x01, y01, -r, a+20)
        line(x01, y01, dx1, dy1, **kwargs)
        line(x01, y01, dx2, dy2, **kwargs)
        line(dx1, dy1, dx2, dy2, **kwargs)
    
    def __repr__(self):
        return "%s(id1=%s, id2=%s)" % (self.__class__.__name__, repr(self.node1.id), repr(self.node2.id))

#--- GRAPH -------------------------------------------------------------------------------------------

# Return value of Graph.shortest_paths().
# Dictionary values can be accessed by Node as well as by node id.
class nodedict(dict):
    def __init__(self, graph):
        self.graph = graph
    def __contains__(self, node):
        return dict.__contains__(self, self.graph.get(node, node))
    def __getitem__(self, node):
        return dict.__getitem__(self, isinstance(node, Node) and node or self.graph[node])
    def get(self, node, default=None):
        return dict.get(self, self.graph.get(node, node), default)

def unique(list):
    u, b = [], {}
    for item in list: 
        if item not in b: u.append(item); b[item]=True
    return u

# Graph layouts:
SPRING = "spring"

# Graph node sort order:
WEIGHT, CENTRALITY = "weight", "centrality"

ALL = "all"

class Graph(dict):
    
    def __init__(self, layout=SPRING, distance=10.0):
        """ A network of nodes connected by edges that can be drawn with a given layout.
        """
        self.nodes      = []   # List of Node objects.
        self.edges      = []   # List of Edge objects.
        self.root       = None
        self._adjacency = None # Cached adjacency() dict.
        self._paths     = {}   # Cached shortest paths.
        self.layout     = layout==SPRING and GraphSpringLayout(self) or GraphLayout(self)
        self.distance   = distance
    
    def __getitem__(self, id):
        try: 
            return dict.__getitem__(self, id)
        except KeyError:
            raise KeyError, "no node with id '%s' in graph" % id
    
    def append(self, base, *args, **kwargs):
        """ Appends a Node or Edge to the graph: Graph.append(Node, id="rabbit").
        """
        kwargs["base"] = base
        if issubclass(base, Node):
            return self.add_node(*args, **kwargs)
        if issubclass(base, Edge):
            return self.add_edge(*args, **kwargs)
    
    def add_node(self, id, *args, **kwargs):
        """ Appends a new Node to the graph.
            An optional base parameter can be used to pass a subclass of Node.
        """
        n = kwargs.pop("base", Node)
        n = isinstance(id, Node) and id or self.get(id) or n(id, *args, **kwargs)
        if n.id not in self:
            self.nodes.append(n)
            self[n.id] = n; n.graph = self
            self.root = kwargs.get("root", False) and n or self.root
            # Clear adjacency cache.
            self._adjacency, self._paths = None, {}
        return n
    
    def add_edge(self, id1, id2, *args, **kwargs):
        """ Appends a new Edge to the graph.
            An optional base parameter can be used to pass a subclass of Edge:
            Graph.add_edge("cold", "winter", base=IsPropertyOf)
        """
        # Create nodes that are not yet part of the graph.
        n1 = self.add_node(id1)
        n2 = self.add_node(id2)
        # Creates an Edge instance.
        # If an edge (in the same direction) already exists, yields that edge instead.
        e1 = n1.links.edge(n2)
        if e1 and e1.node1 == n1 and e1.node2 == n2:
            return e1
        e2 = kwargs.pop("base", Edge)
        e2 = e2(n1, n2, *args, **kwargs)
        self.edges.append(e2)
        # Synchronizes Node.links:
        # A.links.edge(B) yields edge A->B
        # B.links.edge(A) yields edge B->A
        n1.links.append(n2, edge=e2)
        n2.links.append(n1, edge=e1 or e2)
        # Clear adjacency cache.
        self._adjacency, self._paths = None, {}
        return e2        
            
    def remove(self, x):
        """ Removes the given Node (and all its edges) or Edge from the graph.
            Note: removing Edge a->b does not remove Edge b->a.
        """
        if isinstance(x, Node) and x.id in self:
            self.pop(x.id)
            self.nodes.remove(x); x.graph = None
            # Remove all edges involving the given node.
            for e in list(self.edges):
                if x in (e.node1, e.node2):
                    if x in e.node1.links: e.node1.links.remove(x)
                    if x in e.node2.links: e.node2.links.remove(x)
                    self.edges.remove(e) 
        if isinstance(x, Edge):
            self.edges.remove(x)
        # Clear adjacency cache.
        self._adjacency, self._paths = None, {}
    
    def node(self, id):
        """ Returns the node in the graph with the given id.
        """
        return self.get(id)
    
    def edge(self, id1, id2):
        """ Returns the edge between the nodes with given id1 and id2.
        """
        return id1 in self and id2 in self and self[id1].links.edge(id2) or None
    
    def paths(self, node1, node2, length=4, path=[]):
        """ Returns a list of paths (shorter than given length) connecting the two nodes.
        """
        if not isinstance(node1, Node): 
            node1 = self[node1]
        if not isinstance(node2, Node): 
            node2 = self[node2]
        return [[self[id] for id in p] for p in paths(self, node1.id, node2.id, length, path)]
    
    def shortest_path(self, node1, node2, heuristic=None, directed=False):
        """ Returns a list of nodes connecting the two nodes.
        """
        if not isinstance(node1, Node): 
            node1 = self[node1]
        if not isinstance(node2, Node): 
            node2 = self[node2]
        if not len(self._paths) < 1000:
            self._paths = {}
        if node2.id in self._paths.setdefault(node1.id,{}):
            return self._paths[node1.id][node2.id]
        try: 
            p = dijkstra_shortest_path(self, node1.id, node2.id, heuristic, directed)
            p = self._paths[node1.id][node2.id] = [self[id] for id in p]
            return p
        except IndexError:
            return None
            
    def shortest_paths(self, node, heuristic=None, directed=False):
        """ Returns a dictionary of nodes, each linked to a list of nodes (shortest path).
        """
        if not isinstance(node, Node): 
            node = self[node]
        p = nodedict(self)
        for id, path in dijkstra_shortest_paths(self, node.id, heuristic, directed).iteritems():
            p[self[id]] = path and [self[id] for id in path] or None
        return p 
            
    def eigenvector_centrality(self, normalized=True, reversed=True, rating={}, iterations=100, tolerance=0.0001):
        """ Calculates eigenvector centrality and returns a node => weight dictionary.
            Node.weight is updated in the process.
            Node.weight is higher for nodes with a lot of (indirect) incoming traffic.
        """
        ec = eigenvector_centrality(self, normalized, reversed, rating, iterations, tolerance)
        ec = dict((self[id], w) for id, w in ec.iteritems())
        for n, w in ec.iteritems(): 
            n._weight = w
        return ec
            
    def betweenness_centrality(self, normalized=True, directed=False):
        """ Calculates betweenness centrality and returns a node => weight dictionary.
            Node.centrality is updated in the process.
            Node.centrality is higher for nodes with a lot of passing traffic.
        """
        bc = brandes_betweenness_centrality(self, normalized, directed)
        bc = dict((self[id], w) for id, w in bc.iteritems())
        for n, w in bc.iteritems(): 
            n._centrality = w
        return bc
        
    def sorted(self, order=WEIGHT, threshold=0.0):
        """ Returns a list of nodes sorted by WEIGHT or CENTRALITY.
            Nodes with a lot of traffic will be at the start of the list.
        """
        o = lambda node: getattr(node, order)
        nodes = ((o(n), n) for n in self.nodes if o(n) > threshold)
        nodes = reversed(sorted(nodes))
        return [n for w, n in nodes]
        
    def prune(self, depth=0):
        """ Removes all nodes with less or equal links than depth.
        """
        for n in (n for n in self.nodes if len(n.links) <= depth):
            self.remove(n)
            
    def fringe(self, depth=0):
        """ For depth=0, returns the list of leaf nodes (nodes with only one connection).
            For depth=1, returns the list of leaf nodes and their connected nodes, and so on.
        """
        u = []; [u.extend(n.flatten(depth)) for n in self.nodes if len(n.links) == 1]
        return unique(u)
        
    @property
    def density(self):
        # Number of edges vs. maximum number of possible edges.
        # E.g. <0.35 => sparse, >0.65 => dense, 1.0 => complete.
        return 2.0*len(self.edges) / (len(self.nodes) * (len(self.nodes)-1))
        
    @property
    def is_complete(self):
        return self.density == 1.0
    @property
    def is_dense(self):
        return self.density > 0.65
    @property
    def is_sparse(self):
        return self.density < 0.35
        
    def split(self):
        return partition(self)
    
    def update(self, iterations=10, **kwargs):
        """ Graph.layout.update() is called the given number of iterations.
        """
        for i in range(iterations):
            self.layout.update(**kwargs)
        
    def draw(self, weighted=False, directed=False):
        """ Draws all nodes and edges.
        """
        for e in self.edges: 
            e.draw(weighted, directed)
        for n in reversed(self.nodes): # New nodes (with Node._weight=None) first. 
            n.draw(weighted)
            
    def node_at(self, x, y):
        """ Returns the node at (x,y) or None.
        """
        for n in self.nodes:
            if n.contains(x, y): return n
    
    def _add_node_copy(self, n, **kwargs):
        # Magical fairy dust to copy subclasses of Node.
        # We assume that the subclass constructor takes an optional "text" parameter
        # (Text objects in NodeBox for OpenGL's implementation are expensive).
        new = self.add_node(n.id, text=False, root=kwargs.get("root",False))
        new.__class__ = n.__class__
        new.__dict__.update((k, deepcopy(v)) for k,v in n.__dict__.iteritems() 
            if k not in ("graph", "links", "_x", "_y", "force", "_weight", "_centrality"))
    
    def _add_edge_copy(self, e, **kwargs):
        if kwargs.get("node1", e.node1).id not in self \
        or kwargs.get("node2", e.node2).id not in self: 
            return
        new = self.add_edge(
            kwargs.get("node1", self[e.node1.id]), 
            kwargs.get("node2", self[e.node2.id]))
        new.__class__ = e.__class__
        new.__dict__.update((k, deepcopy(v)) for k,v in e.__dict__.iteritems()
            if k not in ("node1", "node2"))
    
    def copy(self, nodes=ALL):
        """ Returns a copy of the graph with the given list of nodes (and connecting edges).
            The layout will be reset.
        """
        g = Graph(layout=None, distance=self.distance)
        g.layout = self.layout.copy(graph=g)
        for n in (nodes==ALL and self.nodes or nodes):
            g._add_node_copy(n, root=self.root==n)
        for e in self.edges: 
            g._add_edge_copy(e)
        return g

#--- GRAPH LAYOUT ------------------------------------------------------------------------------------
# Graph drawing or graph layout, as a branch of graph theory, 
# applies topology and geometry to derive two-dimensional representations of graphs.

class GraphLayout:
    
    def __init__(self, graph):
        """ Calculates node positions iteratively when GraphLayout.update() is called.
        """
        self.graph = graph
        self.iterations = 0
    
    def update(self):
        self.iterations += 1

    def reset(self):
        self.iterations = 0
        for n in self.graph.nodes:
            n._x = 0
            n._y = 0
            n.force = Vector(0,0)
            
    @property
    def bounds(self):
        """ Returns a (x, y, width, height)-tuple of the approximate layout dimensions.
        """
        x0, y0 = +INFINITE, +INFINITE
        x1, y1 = -INFINITE, -INFINITE
        for n in self.graph.nodes:
            if (n.x < x0): x0 = n.x
            if (n.y < y0): y0 = n.y
            if (n.x > x1): x1 = n.x
            if (n.y > y1): y1 = n.y
        return (x0, y0, x1-x0, y1-y0)

    def copy(self, graph):
        return GraphLayout(self, graph)

class GraphSpringLayout(GraphLayout):
    
    def __init__(self, graph):
        """ A force-based layout in which edges are regarded as springs.
            The forces are applied to the nodes, pulling them closer or pushing them apart.
        """
        # Based on: http://snipplr.com/view/1950/graph-javascript-framework-version-001/
        GraphLayout.__init__(self, graph)
        self.k         = 4.0  # Force constant.
        self.force     = 0.01 # Force multiplier.
        self.repulsion = 15   # Maximum repulsive force radius.

    def _distance(self, node1, node2):
        # Yields a tuple with distances (dx, dy, d, d**2).
        # Ensures that the distance is never zero (which deadlocks the animation).
        dx = node2._x - node1._x
        dy = node2._y - node1._y
        d2 = dx*dx + dy*dy
        if d2 < 0.01:
            dx = random() * 0.1 + 0.1
            dy = random() * 0.1 + 0.1
            d2 = dx*dx + dy*dy
        return dx, dy, sqrt(d2), d2

    def _repulse(self, node1, node2):
        # Updates Node.force with the repulsive force.
        dx, dy, d, d2 = self._distance(node1, node2)
        if d < self.repulsion:
            f = self.k**2 / d2
            node2.force.x += f * dx
            node2.force.y += f * dy
            node1.force.x -= f * dx
            node1.force.y -= f * dy
            
    def _attract(self, node1, node2, weight=0, length=1.0):
        # Updates Node.force with the attractive edge force.
        dx, dy, d, d2 = self._distance(node1, node2)
        d = min(d, self.repulsion)
        f = (d2 - self.k**2) / self.k * length
        f *= weight * 0.5 + 1
        f /= d
        node2.force.x -= f * dx
        node2.force.y -= f * dy
        node1.force.x += f * dx
        node1.force.y += f * dy
        
    def update(self, weight=10.0, limit=0.5):
        """ Updates the position of nodes in the graph.
            The weight parameter determines the impact of edge weight.
            The limit parameter determines the maximum movement each update().
        """
        GraphLayout.update(self)
        # Forces on all nodes due to node-node repulsions.
        for i, n1 in enumerate(self.graph.nodes):
            for j, n2 in enumerate(self.graph.nodes[i+1:]):          
                self._repulse(n1, n2)
        # Forces on nodes due to edge attractions.
        for e in self.graph.edges:
            self._attract(e.node1, e.node2, weight*e.weight, 1.0/(e.length or 0.01))
        # Move nodes by given force.
        for n in self.graph.nodes:
            if not n.fixed:
                n._x += max(-limit, min(self.force * n.force.x, limit))
                n._y += max(-limit, min(self.force * n.force.y, limit))
            n.force.x = 0
            n.force.y = 0
            
    def copy(self, graph):
        g = GraphSpringLayout(graph)
        g.k, g.force, g.repulsion = self.k, self.force, self.repulsion
        return g

#--- GRAPH TRAVERSAL ---------------------------------------------------------------------------------

def depth_first_search(node, visit=lambda node: False, traversable=lambda node, edge: True, _visited=None):
    """ Visits all the nodes connected to the given root node, depth-first.
        The visit function is called on each node.
        Recursion will stop if it returns True, and subsequently dfs() will return True.
        The traversable function takes the current node and edge,
        and returns True if we are allowed to follow this connection to the next node.
        For example, the traversable for directed edges is follows:
         lambda node, edge: node == edge.node1
    """
    stop = visit(node)
    _visited = _visited or {}
    _visited[node.id] = True
    for n in node.links:
        if stop: return True
        if not traversable(node, node.links.edge(n)): continue
        if not n.id in _visited:
            stop = depth_first_search(n, visit, traversable, _visited)
    return stop
    
dfs = depth_first_search;

def breadth_first_search(node, visit=lambda node: False, traversable=lambda node, edge: True):
    """ Visits all the nodes connected to the given root node, breadth-first.
    """
    q = [node]
    _visited = {}
    while q:
        node = q.pop(0)
        if not node.id in _visited:
            if visit(node):
                return True
            q.extend((n for n in node.links if traversable(node, node.links.edge(n))))
            _visited[node.id] = True
    return False
        
bfs = breadth_first_search;

def paths(graph, id1, id2, length=4, path=[], _root=True):
    """ Returns a list of paths from node with id1 to node with id2.
        Only paths shorter than the given length are included.
        Uses a brute-force DFS approach (performance drops exponentially for longer paths).
    """
    if len(path) >= length:
        return []
    if id1 not in graph:
        return []
    if id1 == id2:
        return [path + [id1]]
    path = path + [id1]
    p = []
    s = set(path) # 5% speedup.
    for node in graph[id1].links:
        if node.id not in s: 
            p.extend(paths(graph, node.id, id2, length, path, False))
    return _root and sorted(p, key=len) or p

def edges(path):
    """ Returns an iterator of Edge objects for the given list of nodes.
        It yields None where two successive nodes are not connected.
    """
    # For example, the distance (i.e., edge weight sum) of a path:
    # sum(e.weight for e in edges(path))
    return len(path) > 1 and (n.links.edge(path[i+1]) for i,n in enumerate(path[:-1])) or iter(())
    
#--- GRAPH THEORY ------------------------------------------------------------------------------------

def adjacency(graph, directed=False, reversed=False, stochastic=False, heuristic=None):
    """ Returns a dictionary indexed by node id1's,
        in which each value is a dictionary of connected node id2's linking to the edge weight.
        If directed=True, edges go from id1 to id2, but not the other way.
        If stochastic=True, all the weights for the neighbors of a given node sum to 1.
        A heuristic function can be given that takes two node id's and returns
        an additional cost for movement between the two nodes.
    """
    if graph._adjacency is not None and \
       graph._adjacency[1:] == (directed, reversed, stochastic, heuristic):
        return graph._adjacency[0]
    map = {}
    for n in graph.nodes:
        map[n.id] = {}
    for e in graph.edges:
        id1, id2 = not reversed and (e.node1.id, e.node2.id) or (e.node2.id, e.node1.id)
        map[id1][id2] = 1.0 - 0.5 * e.weight
        if heuristic:
            map[id1][id2] += heuristic(id1, id2)
        if not directed: 
            map[id2][id1] = map[id1][id2]
    if stochastic:
        for id1 in map:
            n = sum(map[id1].values())
            for id2 in map[id1]: 
                map[id1][id2] /= n
    # Cache the adjacency map: this makes dijkstra_shortest_path() 2x faster in repeated use.
    graph._adjacency = (map, directed, reversed, stochastic, heuristic)
    return map

def dijkstra_shortest_path(graph, id1, id2, heuristic=None, directed=False):
    """ Dijkstra algorithm for finding the shortest path between two nodes.
        Returns a list of node id's, starting with id1 and ending with id2.
        Raises an IndexError between nodes on unconnected graphs.
    """
    # Based on: Connelly Barnes, http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/119466
    def flatten(list):
        # Flattens a linked list of the form [0,[1,[2,[]]]]
        while len(list) > 0:
            yield list[0]; list=list[1]
    G = adjacency(graph, directed=directed, heuristic=heuristic)
    q = [(0, id1, ())] # Heap of (cost, path_head, path_rest).
    visited = set()    # Visited nodes.
    while True:
        (cost1, n1, path) = heappop(q)
        if n1 not in visited:
            visited.add(n1)
        if n1 == id2:
            return list(flatten(path))[::-1] + [n1]
        path = (n1, path)
        for (n2, cost2) in G[n1].iteritems():
            if n2 not in visited:
                heappush(q, (cost1 + cost2, n2, path))

def dijkstra_shortest_paths(graph, id, heuristic=None, directed=False):
    """ Dijkstra algorithm for finding the shortest paths from the given node to all other nodes.
        Returns a dictionary of node id's, each linking to a list of node id's (i.e., the path).
    """
    # Based on: Dijkstra's algorithm for shortest paths modified from Eppstein.
    # Based on: NetworkX 1.4.1: Aric Hagberg, Dan Schult and Pieter Swart.
    # This is 5x faster than:
    # for n in g: dijkstra_shortest_path(g, id, n.id)
    W = adjacency(graph, directed=directed, heuristic=heuristic)
    Q = [] # Use Q as a heap with (distance, node id)-tuples.
    D = {} # Dictionary of final distances.
    P = {} # Dictionary of paths.
    P[id] = [id] 
    seen = {id: 0} 
    heappush(Q, (0, id))
    while Q:
        (dist, v) = heappop(Q)
        if v in D: continue
        D[v] = dist
        for w in W[v].iterkeys():
            vw_dist = D[v] + W[v][w]
            if w not in D and (w not in seen or vw_dist < seen[w]):
                seen[w] = vw_dist
                heappush(Q, (vw_dist, w))
                P[w] = P[v] + [w]
    for n in graph:
        if n not in P: P[n]=None
    return P

def floyd_warshall_all_pairs_distance(graph, heuristic=None, directed=False):
    """ Floyd-Warshall's algorithm for finding the path length for all pairs for nodes.
        Returns a dictionary of node id's, 
        each linking to a dictionary of node id's linking to path length.
    """
    from collections import defaultdict # Requires Python 2.5+.
    g = graph.keys()
    d = defaultdict(lambda: defaultdict(lambda: 1e30)) # float('inf')
    p = defaultdict(dict) # Predecessors.
    for e in graph.edges:
        u = e.node1.id
        v = e.node2.id
        w = 1.0 - 0.5 * e.weight
        w = heuristic and heuristic(u, v) + w or w
        d[u][v] = min(w, d[u][v])
        d[u][u] = 0
        p[u][v] = u
        if not directed:
            d[v][u] = min(w, d[v][u])
            p[v][u] = v
    for w in g:
        dw = d[w]
        for u in g:
            du, duw = d[u], d[u][w]
            for v in g:
                # Performance optimization, assumes d[w][v] > 0.
                #if du[v] > duw + dw[v]:
                if du[v] > duw and du[v] > duw + dw[v]:
                    d[u][v] = duw + dw[v]
                    p[u][v] = p[w][v]
    return dict((u, dict((v, w) for v,w in d[u].iteritems() if w < 1e30)) for u in d)

def predecessor_path(tree, u, v):
    def _traverse(u, v):
        w = tree[u][v]
        if w == u:
            return []
        return _traverse(u,w) + [w] + _traverse(w,v)
    return [u] + _traverse(u,v) + [v]

def brandes_betweenness_centrality(graph, normalized=True, directed=False):
    """ Betweenness centrality for nodes in the graph.
        Betweenness centrality is a measure of the number of shortests paths that pass through a node.
        Nodes in high-density areas will get a good score.
    """
    # Ulrik Brandes, A Faster Algorithm for Betweenness Centrality,
    # Journal of Mathematical Sociology 25(2):163-177, 2001,
    # http://www.inf.uni-konstanz.de/algo/publications/b-fabc-01.pdf
    # Based on: Dijkstra's algorithm for shortest paths modified from Eppstein.
    # Based on: NetworkX 1.0.1: Aric Hagberg, Dan Schult and Pieter Swart.
    # http://python-networkx.sourcearchive.com/documentation/1.0.1/centrality_8py-source.html
    W = adjacency(graph, directed=directed)
    b = dict.fromkeys(graph, 0.0)
    for id in graph:
        Q = [] # Use Q as a heap with (distance, node id)-tuples.
        D = {} # Dictionary of final distances.
        P = {} # Dictionary of paths.
        for n in graph: P[n]=[]
        seen = {id: 0} 
        heappush(Q, (0, id, id))
        S = []
        E = dict.fromkeys(graph, 0) # sigma
        E[id] = 1
        while Q:    
            (dist, pred, v) = heappop(Q) 
            if v in D: continue
            D[v] = dist
            S.append(v)
            E[v] = E[v] + E[pred]
            for w in W[v].iterkeys():
                vw_dist = D[v] + W[v][w]
                if w not in D and (w not in seen or vw_dist < seen[w]): 
                    seen[w] = vw_dist 
                    heappush(Q, (vw_dist, v, w))
                    P[w] = [v]
                    E[w] = 0
                if vw_dist == seen[w]: # Handle equal paths.
                    P[w].append(v)
                    E[w] = E[w] + E[v] 
        d = dict.fromkeys(graph, 0)  
        while S: 
            w = S.pop() 
            for v in P[w]: 
                d[v] = d[v] + (float(E[v]) / float(E[w])) * (1.0 + d[w]) 
            if w != id: 
                b[w] = b[w] + d[w]
    # Normalize between 0.0 and 1.0.
    m = normalized and max(b.values()) or 1
    b = dict((id, w/m) for id, w in b.iteritems())
    return b

def eigenvector_centrality(graph, normalized=True, reversed=True, rating={}, iterations=100, tolerance=0.0001):
    """ Eigenvector centrality for nodes in the graph (cfr. Google's PageRank).
        Eigenvector centrality is a measure of the importance of a node in a directed network. 
        It rewards nodes with a high potential of (indirectly) connecting to high-scoring nodes.
        Nodes with no incoming connections have a score of zero.
        If you want to measure outgoing connections, reversed should be False.        
    """
    # Based on: NetworkX, Aric Hagberg (hagberg@lanl.gov)
    # http://python-networkx.sourcearchive.com/documentation/1.0.1/centrality_8py-source.html
    # Note: much faster than betweenness centrality (which grows exponentially).
    def normalize(vector):
        w = 1.0 / (sum(vector.values()) or 1)
        for node in vector: 
            vector[node] *= w
        return vector
    G = adjacency(graph, directed=True, reversed=reversed)
    v = normalize(dict([(n, random()) for n in graph])) # Node ID => weight vector.
    # Eigenvector calculation using the power iteration method: y = Ax.
    # It has no guarantee of convergence.
    for i in range(iterations):
        v0 = v
        v  = dict.fromkeys(v0.iterkeys(), 0)
        for n1 in v:
            for n2 in G[n1]:
                v[n1] += 0.01 + v0[n2] * G[n1][n2] * rating.get(n1, 1)
        normalize(v)
        e = sum([abs(v[n]-v0[n]) for n in v]) # Check for convergence.
        if e < len(G) * tolerance:
            # Normalize between 0.0 and 1.0.
            m = normalized and max(v.values()) or 1
            v = dict((id, w/m) for id, w in v.iteritems())
            return v
    warn("node weight is 0 because eigenvector_centrality() did not converge.", Warning)
    return dict((n, 0) for n in G)

# a | b => all elements from a and all the elements from b. 
# a & b => elements that appear in a as well as in b.
# a - b => elements that appear in a but not in b.
def union(a, b):
    return [x for x in a] + [x for x in b if x not in a]
def intersection(a, b):
    return [x for x in a if x in b]
def difference(a, b):
    return [x for x in a if x not in b]

def partition(graph):
    """ Returns a list of unconnected subgraphs.
    """
    # Creates clusters of nodes and directly connected nodes.
    # Iteratively merges two clusters if they overlap.
    # Optimized: about 2x faster than original implementation.
    g = []
    for n in graph.nodes:
        g.append(dict.fromkeys((n.id for n in n.flatten()), True))
    for i in reversed(range(len(g))):
        for j in reversed(range(i+1, len(g))):
            if g[i] and g[j] and len(intersection(g[i], g[j])) > 0:
                g[i] = union(g[i], g[j])
                g[j] = []
    g = [graph.copy(nodes=[graph[id] for id in n]) for n in g if n]
    g.sort(lambda a, b: len(b) - len(a))
    return g
