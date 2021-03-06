"""
Controller module

Contains a remoter controller implementation for sailonline.org
"""
__author__ = "J.R. Versteegh"
__copyright__ = "Copyright 2011, J.R. Versteegh"
__contact__ = "j.r.versteegh@gmail.com"
__version__ = "0.1"
__license__ = "GPLv3, No Warranty. See 'LICENSE'"

import time
from softsailor.utils import *
from softsailor.controller import BoatController, ControllerError
from softsailor.boat import SailBoat
from sol_functions import do_steer, do_steer_wind, fetch_boat

class Controller(BoatController):
    wait_interval = 2
    wait_retry = 20 # Should be multiple of wait_interval
    wait_timeout = 40
    def __optionally_stop_on_tack_or_gybe(self, wind_angle):
        # Stop when tacking or also when gybing in case we're already down on
        # efficiency. This may lead to an overall performance gain
        boat = self.boat
        # If wind angle changed sign: either tack or gybe
        if (wind_angle * boat.wind_angle) < 0:
            # If the boat performance was already down, reset it by stopping
            if boat.efficiency < 0.96: 
                self.stop()

    def steer_heading(self, value):
        boat = self.boat
        heading = normalize_angle_2pi(value)
        wind_angle = normalize_angle_pipi(boat.condition.wind[0] - value)
        self.__optionally_stop_on_tack_or_gybe(wind_angle)
        do_steer(heading)
        fetch_boat(boat)
        secs = 0
        while abs(boat.heading - heading) > 0.001:
            time.sleep(self.wait_interval)
            secs += self.wait_interval
            if secs == self.wait_retry:
                do_steer(heading)
            if secs > self.wait_timeout:
                raise ControllerError("Failed to steer SOL boat")
            fetch_boat(boat)

    def steer_wind_angle(self, value):
        boat = self.boat
        wind_angle = normalize_angle_pipi(value)
        self.__optionally_stop_on_tack_or_gybe(wind_angle)
        do_steer_wind(wind_angle)
        fetch_boat(boat)
        secs = 0
        while abs(boat.wind_angle - wind_angle) > 0.002:
            time.sleep(self.wait_interval)
            secs += self.wait_interval
            if secs == self.wait_retry:
                do_steer_wind(wind_angle)
            if secs > self.wait_timeout:
                raise ControllerError("Failed to steer SOL boat")
            fetch_boat(boat)
        
    def stop(self):
        do_steer_wind(0)
        secs = 0
        while (self.boat.speed > 0.001) or (self.boat.efficiency < 0.999):
            fetch_boat(self.boat)
            time.sleep(self.wait_interval)
            secs += self.wait_interval
            if secs == self.wait_retry:
                do_steer_wind(0)
            if secs > self.wait_timeout:
                raise ControllerError("Failed to stop SOL boat")
