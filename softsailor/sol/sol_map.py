import math
from bisect import bisect, bisect_left, insort
import numpy as np

from softsailor.utils import *
from softsailor.classes import *

from sol_xmlutil import *

def intersection(line1, line2):
    bearing = line1[0].get_bearing_from(line2[0])
    phi = line2[1][0] - bearing[0]
    gamma = line1[1][0] - line2[1][0]
    u = math.cos(phi)
    v = math.sin(phi) * math.cos(gamma)
    sg = math.sin(gamma)
    if sg != 0:
        v /= sg
    else:
        v = 0
    vec = PolarVector(line2[1][0], bearing[1] * (u + v))
    return Position(line2[0]) + vec

def line(p1, p2):
    return (p1, p2 - p1, p2)

def poly_intersect(poly, line):
    result = []
    if line[0][0] > line[2][0]:
        max_line_lat = line[0][0]
        min_line_lat = line[2][0]
    else:
        max_line_lat = line[2][0]
        min_line_lat = line[0][0]
    if line[0][1] > line[2][1]:
        max_line_lon = line[0][1]
        min_line_lon = line[2][1]
    else:
        max_line_lon = line[2][1]
        min_line_lon = line[0][1]
    for poly_part in poly:
        # First check boxes. If they don't intersect, the lines can't either
        if (poly_part[0][0] > max_line_lat \
                    and poly_part[2][0] > max_line_lat) \
                or (poly_part[0][0] < min_line_lat \
                    and poly_part[2][0] < min_line_lat) \
                or (poly_part[0][1] > max_line_lon \
                    and poly_part[2][1] > max_line_lon) \
                or (poly_part[0][1] < min_line_lon \
                    and poly_part[2][1] < min_line_lon):
            continue

        # Now check for actual intersection
        bearing1 = line[2].get_bearing_from(poly_part[0])
        bearing2 = line[2].get_bearing_from(poly_part[2]) 
        phi1 = normalize_angle_pipi(line[1][0] - bearing1[0])
        phi2 = normalize_angle_pipi(line[1][0] - bearing2[0])
        # When the angles have a different sign, the points lie
        # each on different sides of the course line.
        # Further investigation required
        if (phi1 > 0 and phi2 <= 0) or (phi1 <= 0 and phi2 > 0):
            # Now check if the two points of the course segment lie on different 
            # sides of the poly segment. 
            bearing2 = line[0].get_bearing_from(poly_part[0])
            phi1 = normalize_angle_pipi(poly_part[1][0] - bearing1[0])
            phi2 = normalize_angle_pipi(poly_part[1][0] - bearing2[0])
            if (phi1 > 0 and phi2 <= 0) or (phi1 <= 0 and phi2 > 0):
                intersect_point = intersection(poly_part, line)
                print intersect_point
                result.append((poly_part, intersect_point))
    return result

class MapPoint(Position):
    def __init__(self, *args, **kwargs):
        super(MapPoint, self).__init__(*args, **kwargs)
        self.links = []

    def other_link(self, point):
        for link_point in self.links:
            if not link_point is point:
                return link_point
        return None

    @property
    def link1(self):
        if len(self.links) > 0:
            return self.links[0]
        else:
            return None

    @property
    def link2(self):
        if len(self.links) > 1:
            return self.links[1]
        else:
            return None


class Map:
    def load(self, mapurl):
        dom = fetch_sol_document_from_url(mapurl)
        root = dom.childNodes[0]

        cellmap = get_element(root, 'cellmap')
        self.minlat = deg_to_rad(float(cellmap.getAttribute('minlat')))
        self.maxlat = deg_to_rad(float(cellmap.getAttribute('maxlat')))
        self.minlon = deg_to_rad(float(cellmap.getAttribute('minlon')))
        self.maxlon = deg_to_rad(float(cellmap.getAttribute('maxlon')))
        self.cellsize = deg_to_rad(float(cellmap.getAttribute('cellsize')))

        lat_cells = int(round((self.maxlat - self.minlat) / self.cellsize))
        lon_cells = int(round((self.maxlon - self.minlon) / self.cellsize))
        self.cells = [[[] for i in range(lon_cells)] for j in range(lat_cells)]
        cells = get_elements(cellmap, 'cell')
        for cell in cells:
            cell_minlat = deg_to_rad(float(cell.getAttribute('minlat')))
            cell_minlon = deg_to_rad(float(cell.getAttribute('minlon')))
            lat_i = int(round((cell_minlat - self.minlat) / self.cellsize))
            lon_i = int(round((cell_minlon - self.minlon) / self.cellsize))
            polys = get_elements(cell, 'poly')
            for poly in polys:
                pl = []
                points = get_elements(poly, 'point')
                pos2 = None
                for point in points:
                    lat = float(point.getAttribute('lat'))
                    lon = float(point.getAttribute('lon'))
                    pos1 = Position(deg_to_rad(lat), deg_to_rad(lon))
                    if not pos2 is None and not pos2 == pos1:
                        # Avoid adding grid lines
                        looks_like_grid = False
                        if pos1[0] == pos2[0]: 
                            # This line is horizontal
                            rounded = round(pos1[0] / self.cellsize)
                            rounded *= self.cellsize
                            if np.allclose(pos1[0], rounded):
                                looks_like_grid = True
                        if pos1[1] == pos2[1]: 
                            # This line is vertical
                            rounded = round(pos1[1] / self.cellsize)
                            rounded *= self.cellsize
                            if np.allclose(pos1[1], rounded):
                                looks_like_grid = True
                        if not looks_like_grid:
                            pl.append((pos1, pos2 - pos1, pos2))
                    pos2 = pos1
                if len(pl) > 0:
                    self.cells[lat_i][lon_i].append(pl)

        dom.unlink()
        self.__connect()

    def __hit(self, line):
        result = None
        dist = line[1][1]
        i1 = int(math.floor((line[0][0] - self.minlat) / self.cellsize))
        j1 = int(math.floor((line[0][1] - self.minlon) / self.cellsize))
        i2 = int(math.floor((line[2][0] - self.minlat) / self.cellsize))
        j2 = int(math.floor((line[2][1] - self.minlon) / self.cellsize))
        min_i = min(i1, i2)
        max_i = max(i1, i2)
        min_j = min(j1, j2)
        max_j = max(j1, j2)
        for i in range(min_i, max_i + 1):
            for j in range(min_j, max_j + 1):   
                for pl in self.cells[i][j]:
                    intersects = poly_intersect(pl, line) 
                    if intersects:
                        for poly_part, intersect_point in intersects:
                            intersect_bearing = line[0].get_bearing_to(intersect_point)
                            if intersect_bearing[1] < dist:
                                result = poly_part
                                dist = intersect_bearing[1]
        return result

    def hit(self, line):
        poly_part = self.__hit(line)
        if poly_part:
            return True
        else:
            return False

    def outer(self, line):
        poly_part = self.__hit(line)
        p_outer = [None, None]
        if not poly_part is None:
            # Line intersects with land
            p = [self.__find_point(poly_part[0]), \
                 self.__find_point(poly_part[2])]
            p_from = Position(line[0])
            b = [p[0].get_bearing_from(p_from), \
                 p[1].get_bearing_from(p_from) ]
            b_outer = [None, None]
            if b[1].is_left_of(b[0]):
                direction = 1
            else:
                direction = 0

            def trace_poly(forward, right):
                print "Trace forward: %d direct %d" % (forward, right)
                p_cur = p[forward]
                # Remember last point in order to maintain direction
                p_last = p[1 - forward]
                # While there is a next point and we haven't gone completely round
                while p_cur and not p_cur is p[1 - forward]:
                    b_cur = p_cur.get_bearing_from(p_from)
                    print p_last, p_cur, b_cur
                    # Only when point is closer then line length, otherwise
                    # the point will never be reached
                    if b_cur[1] < line[1][1]:
                        if b_cur.is_side_of(b_outer[right], right):
                            b_outer[right] = b_cur
                            p_outer[right] = p_cur
                            print 'Outer: ', p_outer[right], b_outer[right]
                    else:
                        print "Out of reach"

                    p_next = p_cur.other_link(p_last)
                    p_last = p_cur
                    p_cur = p_next

                # Poly ended (edge of map?). That's not a way around
                if not p_cur and p_last is p_outer[right]:
                    p_outer[right] = None

            trace_poly(0, direction)
            trace_poly(1, 1 - direction)

        return p_outer

                

    def __find_point(self, point):
        i = bisect_left(self.points, point)
        if i != len(self.points) and self.points[i] == point:
            return self.points[i]
        else:
            return None
    
    def __connect(self):
        self.points = []
        for cell_row in self.cells:
            for cell in cell_row:
                for polys in cell:
                    for poly_part in polys:
                        p1 = self.__find_point(poly_part[0])
                        p2 = self.__find_point(poly_part[2])
                        if p1 is None:
                            p1 = MapPoint(poly_part[0])
                            insort(self.points, p1)
                        if p2 is None:
                            p2 = MapPoint(poly_part[2])
                            insort(self.points, p2)
                        p1.links.append(p2)
                        p2.links.append(p1)


