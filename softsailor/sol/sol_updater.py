"""
This module contains boat updater implementations for sailonline.org

Author: Jaap Versteegh <j.r.versteegh@gmail.com>
"""
from softsailor.updater import BoatUpdater, SimUpdater as BaseSimUpdater
from sol_functions import fetch_boat

from datetime import timedelta

class Updater(BoatUpdater):
    def update(self):
        fetch_boat(self.boat)
        self.log()

class SimUpdater(BaseSimUpdater):
    """
    Simulation updater that implements approximation of SOL
    performance penalty by fast forwarding the boat clock
    """
    prev_wind_angle = None
    def update(self):
        super(SimUpdater, self).update()
        wind_angle = self.boat.wind_angle
        if self.prev_wind_angle != None:
            penalty = abs(wind_angle - self.prev_wind_angle) 
            if (wind_angle * self.prev_wind_angle) < 0:
                # Tacked or gybed
                penalty += 1.5 
            speed = self.boat.speed
            penalty *= 0.2 * speed * speed
            self.boat.time += timedelta(seconds=round(penalty))
        self.prev_wind_angle = wind_angle
