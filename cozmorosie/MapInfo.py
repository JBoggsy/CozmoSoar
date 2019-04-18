from math import *

class RectRegion:
    """ 
    RectRegion defines a rectangular region in the xy plane 
    You can then test to see if a given point lies inside that region
    """
    def __init__(self, config_line):
        """ 
        Initialized from a line in a config file - 
        a space-separated list of values:
            id x y rot width length label 
        id - The id for the region
        x, y - The coordinates for the center of the rectangle (inches)
        rot - The rotation of the rectangle
        width, length - The dimensions of the region (inches)
        label - the type of region (hall, room, etc.)
        """

        params = config_line.split(" ")
        if len(params) < 7:
            pass

        self.id = params[0]
        self.x = float(params[1]) 
        self.y = float(params[2])
        self.rot = float(params[3])
        self.width = float(params[4])
        self.length = float(params[5])
        self.label = params[6]

    def get_distance_sq(self, point):
        """ 
        Returns the distance squared between the center of the region and the given point
        point: list or tuple of 2 floats, x and y in decimeters
        """
        dx = point[0] - self.x
        dy = point[1] - self.y
        return (dx*dx + dy*dy)

    def contains_point(self, point):
        """
        Returns True if the given point is inside the region
        point: list or tuple of 2 floats, x and y in decimeters
        """
        dx = point[0] - self.x
        dy = point[1] - self.y
        dist = sqrt(dx*dx + dy*dy)
        theta = atan2(dy, dx)
        localTheta = theta - self.rot
        xproj = dist * cos(localTheta)
        yproj = dist * sin(localTheta)
        return (abs(xproj) < self.width/2 and abs(yproj) < self.length/2)

    def __str__(self):
        return "{}: ({}, {}) r{} {}x{}".format(self.id, self.x, self.y, self.rot, self.width, self.length)


class MapInfo:
    """
    Reads a map info file and creates a dict of regions which 
    can be used to see which region the robot is currently in
    """

    # map-info-file
    def __init__(self, map_filename=None):
        self.regions = {}
        self.robot_pos = (0.0, 0.0)

        if map_filename:
            self.read_map_info(map_filename)

    def get_robot_pos(self):
        return self.robot_pos

    def get_all_regions(self):
        return list(self.regions.values())

    def get_containing_regions(self, point):
        return [ reg for reg in self.regions.values() if reg.contains_point(point) ]

    def read_map_info(self, map_filename):
        with open(map_filename, 'r') as f:
            for line in f:
                line = line[:-1] # Remove trailing newline
                words = line.split(" ")
                if words[0] == "robot":
                    if len(words) >= 3:
                        self.robot_pos = ( float(words[1]), float(words[2]) )
                elif len(words) >= 7:
                    reg = RectRegion(line)
                    self.regions[reg.id] = reg
    
