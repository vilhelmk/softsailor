"""
Classes module

Contains utility classes
"""
__author__ = "J.R. Versteegh"
__copyright__ = "Copyright 2011, J.R. Versteegh"
__contact__ = "j.r.versteegh@gmail.com"
__version__ = "0.1"
__license__ = "GPLv3, No Warranty. See 'LICENSE'"

import math
import numpy as np
from datetime import timedelta

from utils import *

def dxy_dpos(latitude, longitude):
    """Simple earth model"""
    return 6367311.8, 6378134.3 * math.cos(latitude)

class Vector(object):
    def __init__(self, *args, **kwargs):
        super(Vector, self).__init__()
        if type(self) == Vector:
            raise TypeError('Construct a PolarVector or CartesianVector instead')

    @property
    def ar(self):
        return self.a, self.r

    @ar.setter
    def ar(self, value):
        self.a, self.r = value

    @property
    def xy(self):
        return self.x, self.y

    @xy.setter
    def xy(self, value):
        self.x, self.y = value

    @property
    def sa(self):
        return normalize_angle_pipi(self.a)

    def __getitem__(self, index):
        if index == 0:
            return self.a
        elif index == 1:
            return self.r
        else:
            raise IndexError("Vector index should be 0 or 1")

    def __setitem__(self, index, value):
        if index == 0:
            self.a = value
        elif index == 1:
            self.r = value
        else:
            raise IndexError("Vector index should be 0 or 1")

    def __len__(self):
        return 2

    def __iter__(self):
        return iter((self.a, self.r))

    def __iadd__(self, vector):
        self.x += vector.x
        self.y += vector.y
        return self

    def __isub__(self, vector):
        self.x -= vector.x
        self.y -= vector.y
        return self

    def __imul__(self, scalar):
        if isinstance(scalar, timedelta):
            self.r *= timedelta_to_seconds(scalar)
        else:
            self.r *= scalar
        return self

    def __add__(self, vector):
        result = CartesianVector(self.xy)
        result += vector
        return result

    def __sub__(self, vector):
        result = CartesianVector(self.xy)
        result -= vector
        return result

    def __mul__(self, scalar):
        result = PolarVector(self)
        result *= scalar
        return result

    def __neg__(self):
        return CartesianVector(-self.x, -self.y)

    def __str__(self):
        r = self.r
        if r >= 50:
            return "(%.2f, %.2f)" \
                    % (rad_to_deg(self.a), m_to_nm(r))
        else:
            return "(%.2f, %.2f)" \
                    % (rad_to_deg(self.a), ms_to_kn(r))

    def __eq__(self, vector):
        vec = (normalize_angle_2pi(vector[0]), vector[1])
        return np.allclose(self, vec)
    
    def __lt__(self, vector):
        return self.r < vector[1]

    def __gt__(self, vector):
        return self.r > vector[1]

    def __le__(self, vector):
        return self.r <= vector[1]

    def __ge__(self, vector):
        return self.r >= vector[1]

    def dot(self, vector):
        return self.x * vector.x + self.y * vector.y

    def cross(self, vector):
        return self.x * vector.y - self.y * vector.x 

    

class PolarVector(Vector):
    def __init__(self, *args, **kwargs):
        super(PolarVector, self).__init__(*args, **kwargs)
        self.a = kwargs.get('a', 0)
        self.r = kwargs.get('r', 0)
        if len(args) > 1:
            self.a, self.r = args
        else:
            self.a, self.r = args[0]

    @property
    def x(self):
        return self.r * math.cos(self.a)

    @x.setter
    def x(self, value):
        y = self.y
        self.a = math.atan2(y, value)
        if y < 0:
            self.a += two_pi
        self.r = math.hypot(value, y)

    @property
    def y(self):
        return self.r * math.sin(self.a)

    @y.setter
    def y(self, value):
        x = self.x
        self.a = math.atan2(value, x)
        if value < 0:
            self.a += two_pi
        self.r = math.hypot(x, value)

    # Performance overloads
    def __neg__(self):
        result = PolarVector(self)
        result.a -= math.pi
        if result.a < 0:
            result.a += two_pi
        return result

    @Vector.xy.setter
    def xy(self, value):
        self.a = math.atan2(value[1], value[0])
        if self.a < 0:
            self.a += two_pi
        self.r = math.hypot(value[0], value[1])

class CartesianVector(Vector):
    def __init__(self, *args, **kwargs):
        super(CartesianVector, self).__init__(*args, **kwargs)
        self.x = kwargs.get('x', 0)
        self.y = kwargs.get('y', 0)
        if len(args) > 1:
            self.x, self.y = args
        else:
            self.x, self.y = args[0]

    @property
    def a(self):
        a = math.atan2(self.y, self.x)
        if a < 0:
            a += two_pi
        return a

    @a.setter
    def a(self, value):
        r = self.r
        self.x = r * math.cos(value)
        self.y = r * math.sin(value)

    @property
    def r(self):
        return math.hypot(self.x, self.y)

    @r.setter
    def r(self, value):
        a = self.a
        self.x = value * math.cos(a)
        self.y = value * math.sin(a)

    # Performance overloads
    def __imul__(self, scalar):
        self.x *= scalar
        self.y *= scalar
        return self

    @Vector.ar.setter
    def ar(self, value):
        self.x = value[1] * math.cos(value[0])
        self.y = value[1] * math.sin(value[0])

class Bearing(PolarVector):
    def is_left_of(self, other):
        if other is None:
            return True
        return angle_diff(self.a, other[0]) < 0

    def is_right_of(self, other):
        if other is None:
            return True
        return angle_diff(self.a, other[0]) > 0

    def is_side_of(self, other, right):
        if right:
            return self.is_right_of(other)
        else:
            return self.is_left_of(other)

class Position(object):
    def __init__(self, *args, **kwargs):
        super(Position, self).__init__()
        self.latitude = kwargs.get('latitude', 0)
        self.longitude = kwargs.get('longitude', 0)
        if len(args) > 1:
            self.latitude, self.longitude = args
        else:
            self.latitude, self.longitude = args[0]

        # Initialize earth model
        self.dxy_dpos = dxy_dpos

    @property
    def dxy(self):
        return self.dxy_dpos(self.latitude, self.longitude) 

    @vec_func
    def get_bearing_from(self, lat, lon):
        dxy1 = self.dxy
        dxy2 = self.dxy_dpos(lat, lon)
        dx = 0.5 * (dxy1[0] + dxy2[0])
        dy = 0.5 * (dxy1[1] + dxy2[1])
        x = dx * (self.latitude - lat)
        y = dy * (self.longitude - lon)
        result = Bearing(0, 0)
        result.xy = (x, y)
        return result

    @vec_func
    def get_bearing_to(self, lat, lon):
        result = self.get_bearing_from(lat, lon)
        result = -result
        return result

    def __getitem__(self, index):
        if index == 0:
            return self.latitude
        elif index == 1:
            return self.longitude
        else:
            raise IndexError("Position index should be 0 or 1")

    def __setitem__(self, index, value):
        if index == 0:
            self.latitude = value
        elif index == 1:
            self.longitude = value
        else:
            raise IndexError("Position index should be 0 or 1")

    def __iadd__(self, vector):
        dxy = list(self.dxy)
        new_lat = self.latitude + vector.x / dxy[0]
        new_lon = self.longitude + vector.y / dxy[1]
        dxy_new = self.dxy_dpos(new_lat, new_lon) 
        dxy[0] = 0.5 * (dxy[0] + dxy_new[0])
        dxy[1] = 0.5 * (dxy[1] + dxy_new[1])

        self.latitude += vector.x / dxy[0]
        self.longitude += vector.y / dxy[1]
        return self

    def __isub__(self, vector):
        dxy = list(self.dxy)
        new_lat = self.latitude - vector.x / dxy[0]
        new_lon = self.longitude - vector.y / dxy[1]
        dxy_new = self.dxy_dpos(new_lat, new_lon) 
        dxy[0] = 0.5 * (dxy[0] + dxy_new[0])
        dxy[1] = 0.5 * (dxy[1] + dxy_new[1])
        self.latitude -= vector.x / dxy[0]
        self.longitude -= vector.y / dxy[1]
        return self

    def __add__(self, vector):
        result = Position(self)
        result += vector
        return result

    def __sub__(self, vector_or_position):
        if isinstance(vector_or_position, Position):
            result = self.get_bearing_from(vector_or_position)
        else:
            result = Position(self)
            result -= vector_or_position
        return result

    def __eq__(self, position):
        if position is None:
            return False
        return np.allclose(self, position)

    def __cmp__(self, position):
        if self.latitude < position[0]:
            return -1
        elif self.latitude > position[0]:
            return 1
        elif self.longitude < position[1]:
            return -1
        elif self.longitude > position[1]:
            return 1
        else:
            return 0

    def __str__(self):
        return '(' + "%.4f" % rad_to_deg(self.latitude) + ', ' \
               + "%.4f" % rad_to_deg(self.longitude) + ')'

    def __len__(self):
        return 2


class PolarData:
    speeds = []
    angles = []
    data = []

