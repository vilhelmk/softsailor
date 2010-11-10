import os
import math
from xml.dom.minidom import parseString, getDOMImplementation
# These are from libkml. You may need to install these
import kmlbase
import kmldom
import kmlengine

def get_config_dir():
    script_path = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.realpath(script_path + '/../etc')
    return config_path

def timedelta_to_seconds(td):
    return td.days * 86400 + td.seconds + td.microseconds * 1E-6

def array_func(func):
    def decorated(*args):
        if len(args) > 1:
            return list(map(func, args))
        else:
            arg = args[0]
            t = type(arg)
            if t == str or t == unicode:
                return func(arg)
            else:
                try:
                    it = iter(arg)
                    return type(arg)(map(func, arg))
                except TypeError:
                    return func(arg)
    return decorated

def vec_func(func):
    def decorated(*args):
        if len(args) > 1:
            return func((args[0], args[1]))
        else:
            return func(args[0])
    return decorated

def vec_meth(func):
    def decorated(self, *args):
        if len(args) > 1:
            return func(self, (args[0], args[1]))
        else:
            return func(self, args[0])
    return decorated

@array_func
def deg_to_rad(degs):
    return math.radians(float(degs))

@array_func
def rad_to_deg(rads):
    return math.degrees(float(rads))

@array_func
def knots_to_ms(knots):
    return float(knots) * 1852 / 3600

@array_func
def ms_to_knots(ms):
    return ms * 3600 / 1852

@array_func
def to_float(value):
    return float(value)

@array_func
def to_string(value):
    return str(value)

def add_element_with_text(dom, parent, name, text):
    """Adds an xml element with 'name' and containing 'text' to a existing
       element 'parent'
    """
    element = dom.createElement(name)
    parent.appendChild(element)
    text_node = dom.createTextNode(text)
    element.appendChild(text_node)
    return element

def create_kml_document(name):
    factory = kmldom.KmlFactory_GetFactory()
    doc = factory.CreateDocument()
    doc.set_name(name)
    kml = factory.CreateKml()
    kml.set_feature(doc)
    return (factory, kml)

def save_kml_document(kml, filename):
    f = open(filename, 'w')
    f.write(kmldom.SerializePretty(kml))
    f.close()

two_pi = 2 * math.pi

def normalize_angle_pipi(angle):
    # Normalize angle in -180 <= angle < 180 range
    while angle >= math.pi:
        angle -= two_pi
    while angle < -math.pi:
        angle += two_pi
    return angle

def normalize_angle_2pi(angle):
    # Normalize angle in 0 <= angle < 360 range
    while angle >= two_pi:
        angle -= two_pi
    while angle < 0:
        angle += two_pi
    return angle

def rectangular_to_polar(vector):
    return (normalize_angle_2pi(math.atan2(vector[1], vector[0])),  \
            math.sqrt(vector[0] * vector[0] + vector[1] * vector[1]))

def polar_to_rectangular(vector):
    return (vector[1] * cos(vector[0]), vector[1] * sin(vector[0]))

def bearing_to_heading(bearing, speed, current):
    result = bearing[0]
    if speed != 0 and current[1] != 0:
        result += math.asin(current[1] * math.sin(bearing[0] + current[0]) / speed)
        normalize_angle_2pi(result)
    return result
        

