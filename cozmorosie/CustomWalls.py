
import cozmo

from cozmo.objects import CustomObjectMarkers as COM
from cozmo.objects import CustomObjectTypes as COT



def define_custom_walls(cozmo_world):
    # Defines bricks (12" x 6" x 3")
    marker_types = [
        COT.CustomType00,
        COT.CustomType01,
        COT.CustomType02,
        COT.CustomType03,
        COT.CustomType04,
        COT.CustomType05,
        COT.CustomType06,
        COT.CustomType07,
        COT.CustomType08
    ]
    marker_symbols = [ COM.Triangles3, COM.Triangles4, COM.Triangles5,
                        COM.Diamonds3, COM.Diamonds4, COM.Diamonds5, 
                        COM.Hexagons3, COM.Hexagons4, COM.Hexagons5 ]
    for i in range(9):
        cozmo_world.define_custom_wall(marker_types[i], marker_symbols[i], 
                width_mm=305, height_mm=152, marker_width_mm=38, marker_height_mm=38)

def define_custom_cubes(cozmo_world):
    marker_types = [ COT.CustomType17,  COT.CustomType18, COT.CustomType19 ]
    marker_symbols = [ COM.Circles3, COM.Circles4, COM.Circles5]
    for i in range(3):
        cozmo_world.define_custom_cube(marker_types[i], marker_symbols[i], 
                size_mm=50, marker_width_mm=38, marker_height_mm=38)





