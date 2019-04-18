
import cozmo

from cozmo.objects import CustomObjectTypes, CustomObjectMarkers


def define_custom_walls(cozmo_world):
    cozmo_world.define_custom_wall(CustomObjectTypes.CustomType00, CustomObjectMarkers.Circles2, 
            width_mm=305, height_mm=152, marker_width_mm=38, marker_height_mm=38)
    cozmo_world.define_custom_wall(CustomObjectTypes.CustomType00, CustomObjectMarkers.Triangles2, 
            width_mm=305, height_mm=152, marker_width_mm=38, marker_height_mm=38)
    cozmo_world.define_custom_wall(CustomObjectTypes.CustomType00, CustomObjectMarkers.Hexagons2, 
            width_mm=305, height_mm=152, marker_width_mm=38, marker_height_mm=38)
    cozmo_world.define_custom_wall(CustomObjectTypes.CustomType00, CustomObjectMarkers.Diamonds2, 
            width_mm=305, height_mm=152, marker_width_mm=38, marker_height_mm=38)
    cozmo_world.define_custom_wall(CustomObjectTypes.CustomType00, CustomObjectMarkers.Triangles3, 
            width_mm=305, height_mm=152, marker_width_mm=38, marker_height_mm=38)


