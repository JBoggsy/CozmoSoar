
import cozmo

from cozmo.objects import CustomObjectTypes, CustomObjectMarkers


def define_custom_walls(cozmo_world):
    cozmo_world.define_custom_wall(CustomObjectTypes.CustomType00, CustomObjectMarkers.Circles2, 
            width_mm=305, height_mm=152, marker_width_mm=38, marker_height_mm=38)


