from utils import *
from classes import *
from controller import ControllerError

from datetime import datetime

class Sailor(object):
    """Handles sailing a boat along a route"""
    __log_data = []

    def __init__(self, *args, **kwargs):
        super(Sailor, self).__init__()
        if len(args) > 0:
            self.boat = args[0]
            self.controller = args[1]
            self.updater = args[2]
            self.router = args[3]
            self.map = args[4]
        else:
            self.boat = kwargs['boat']
            self.controller = kwargs['controller']
            self.updater = kwargs['updater']
            self.router = kwargs['router']
            self.map = kwargs['map']

    def __log(self, log_string):
        self.__log_data.append((datetime.utcnow(), log_string))

    def save_log(self, filename):
        f = open(filename + '.txt', "w")
        for record in self.__log_data:
            f.write(str(record[0]) + " " + record[1] + "\n")
        f.close()

    def sail(self):
        self.updater.update()
        if self.router.is_complete:
            return False
        new_heading = self.get_heading()
        if abs(new_heading - self.boat.heading) > 0.004:
            try: 
                self.__log("Steering %.2f" % rad_to_deg(new_heading))
                self.controller.steer_heading(new_heading)
            except ControllerError:
                self.__log("Failed to steer boat")
                
        return True
        
    def get_heading(self):
        bearing = self.router.get_bearing()
        if self.router.is_complete:
            return self.boat.heading
        heading = bearing_to_heading(bearing, \
                self.boat.speed, self.boat.condition.current) 
        changed, heading = self.adjust_heading_for_wind(heading)
        if changed:
            # These are only required when we're not headed directly for the
            # waypoint
            changed, heading = self.handle_tacking_and_gybing(heading, bearing)
            changed, heading = self.prevent_beaching(heading)
        return heading

    def adjust_heading_for_wind(self, heading):
        wind = self.boat.condition.wind
        # Check the suggested heading for suboptimal wind angles
        wind_angle = normalize_angle_pipi(wind[0] - heading)
        if wind_angle < 0:
            abs_wind_angle = -wind_angle
            sign = -1
        else:
            abs_wind_angle = wind_angle
            sign = 1
        opt_angles = self.boat.performance.get_optimal_angles(wind[1])
        # Clip the wind angle to the optimal range...
        if abs_wind_angle < opt_angles[0]:
            new_wind_angle = opt_angles[0] * sign
        elif abs_wind_angle > opt_angles[1]:
            new_wind_angle = opt_angles[1] * sign
        else:
            # Heading indicated a sailable course
            return False, heading
        # ...and return a heading resulting from this wind angle
        return True, normalize_angle_2pi(new_wind_angle + wind[0])

    def handle_tacking_and_gybing(self, heading, bearing):
        wind = self.boat.condition.wind
        wind_angle = normalize_angle_pipi(wind[0] - heading)
        track, waypoint = self.router.get_active_segment()

        if (wind_angle < 0) != (self.boat.wind_angle < 0):
            # A tack or gybe is apparently suggested...
            # ...revert it in order to prevent excessive tacking/gybing
            heading = normalize_angle_2pi(heading + 2 * wind_angle)

        # If we're not too far off track, we'll have to tack/gybe
        allowed_off_track = waypoint.range + 25 * math.sqrt(bearing[1])
        off_track = self.router.get_cross_track()
        if abs(off_track) > allowed_off_track:
            # ... in which case we'll make sure we steer on a
            # converging tack/reach
            track_angle = normalize_angle_pipi(heading - track[0])
            # Check if heading and track line converge...
            if (off_track > 0) == (track_angle > 0):
                # ...or tack/gybe when they don't
                self.__log("Tacked/gybed to reduce CTE")
                return True, normalize_angle_2pi(heading + 2 * wind_angle)
    

        # Nothing needed to be done. Return the originally suggested heading
        return False, heading

    def prevent_beaching(self, heading, look_ahead = None):
        if look_ahead == None:
            look_ahead = 250
        # We'll construct a future course line...
        boat_position = self.boat.position
        # ... project it ahead...
        sail_vector = PolarVector(heading, look_ahead)
        future_position = boat_position + sail_vector
        sail_line = (self.boat.position, sail_vector, future_position)
        # Check if the projected line hits land...
        if self.map.hit(sail_line):
            # ... and if so, tack or gybe away from it
            wind = self.boat.condition.wind
            wind_angle = normalize_angle_pipi(wind[0] - heading)
            self.__log("Tacked/gybed to avoid hitting land")
            return True, normalize_angle_2pi(heading + 2 * wind_angle)

        # Also, we want to keep a clear line of sight to the waypoint
        waypoint = self.router.active_waypoint
        bearing = waypoint.get_bearing_from(self.boat.position)
        view_line = (self.boat.position, bearing, waypoint)
        if self.map.hit(view_line):
            # The only way, we could have gotten something in the view
            # line is that we were reaching or tacking away from the
            # track. Tack or gybe now to get back.
            wind = self.boat.condition.wind
            wind_angle = normalize_angle_pipi(wind[0] - heading)
            self.__log("Tacked/gybed to avoid land getting in line of sight")
            return True, normalize_angle_2pi(heading + 2 * wind_angle)

        # Nothing needed to be done. Return the originally suggested heading
        return False, heading

