# 2D physics functions.
# Authors: Tom De Smedt, Giorgio Olivero (Vector class)
# License: GPL (see LICENSE.txt for details).
# Copyright (c) 2008 City In A Bottle (cityinabottle.org)

from math   import sqrt, pow
from math   import sin, cos, atan2, degrees, radians, pi
from random import random, shuffle

_UID = 0
def _uid():
    global _UID; _UID+=1; return _UID
    
def shuffled(list):
    indices = range(len(list))
    shuffle(indices)
    for i in indices: 
        yield(list[i])

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
        self.x = cos(radians(-degrees)) * d
        self.y = sin(radians(-degrees)) * d
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
        """ Returns a new vector that is the dot product between the two vectors.
        """
        return self * v
        
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
        return "%s(%s, %s, %s)" % (self.__class__.__name__, self.x, self.y, self.z)

    def draw(self, x, y, arrow=5):
        """ Draws the vector in 2D (z-axis is ignored). 
            Set stroke() and strokewidth() first.
        """
        from context import line, push, transform, translate, rotate, pop
        line(x, y, x+self.x, y+self.y)
        push()
        translate(x+self.x, y+self.y)
        rotate(self.angle)
        line(0, 0, -arrow, -arrow*0.5)
        line(0, 0, -arrow, +arrow*0.5)
        pop()

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

class Boid:
    
    def __init__(self, flock, x=0, y=0, z=0, sight=70, space=30):
        """ An agent in a flock with an (x,y,z)-position subject to different forces.
            - sight : radius of local flockmates when calculating cohesion and alignment.
            - space : radius of personal space when calculating separation.
        """
        self.id       = _uid()
        self.flock    = flock
        self.x        = x
        self.y        = y
        self.z        = z
        self.velocity = Vector(random()*2-1, random()*2-1, random()*2-1)
        self.target   = None  # A target Vector towards which the boid will steer.
        self.sight    = sight # The radius of cohesion ang alignment, and visible obstacles.
        self.space    = space # The radius of separation.
    
    def __eq__(self, other):
        # Comparing boids by id makes it significantly faster.
        return isinstance(other, Boid) and self.id == other.id
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
        if n: 
            return (vx/n-self.x), (vy/n-self.y), (vz/n-self.z)
        return vx, vy, vz

    def avoidance(self):
        """ Returns steering velocity (vx,vy,0) to avoid 2D obstacles.
            The boid is not guaranteed to avoid collision.
        """
        vx = vy = 0.0
        for o in self.flock.obstacles:
            dx = o.x - self.x
            dy = o.y - self.y
            d = sqrt(dx**2 + dy**2)     # Distance to obstacle.
            s = (self.sight + o.radius) # Visibility range.
            if d < s:
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
        m = max(abs(v.x), abs(v.y), abs(v.z))
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
        
def flock(amount, x, y, width, height, depth=1.0):
    return Boids(amount, x, y, width, height, depth)
