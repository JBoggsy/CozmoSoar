import sys
from math import sqrt, atan2, pi

from cozmo.lights import green_light, red_light, blue_light, white_light, off_light, Color, Light
from cozmo.objects import CustomObjectMarkers, CustomObjectTypes, _CustomObjectType

#################
# DEFINE COLORS #
#################
brown_color = Color(name="brown",
                    rgb=(80, 20, 0))
yellow_color = Color(name="yellow",
                     rgb=(255, 255, 0))
orange_color = Color(name="orange",
                     rgb=(255, 80, 0))
purple_color = Color(name="purple",
                     rgb=(255, 0, 255))
teal_color = Color(name="teal",
                   rgb=(0, 255, 255))

brown_light = Light(on_color=brown_color)
yellow_light = Light(on_color=yellow_color)
orange_light = Light(on_color=orange_color)
purple_light = Light(on_color=purple_color)
teal_light = Light(on_color=teal_color)

COLORS = ["red", "blue", "green",
          "brown", "yellow", "orange",
          "purple", "teal", "white",
          "off"]
LIGHTS = [red_light, blue_light, green_light,
          brown_light, yellow_light, orange_light,
          purple_light, teal_light, white_light,
          off_light]
LIGHTS_DICT = dict(zip(COLORS, LIGHTS))

RED_STR = "\u001b[31m" if sys.platform != "win32" else ""
GREEN_STR = "\u001b[32m" if sys.platform != "win32" else ""
BLUE_STR = "\u001b[34m" if sys.platform != "win32" else ""
RESET_STR = "\u001b[0m" if sys.platform != "win32" else ""

COZMO_COMMANDS = [
    "move-lift",
    "go-to-object",
    "move-head",
    "turn-to-face",
    "turn-to-object",
    "set-backpack-lights",
    "drive-forward",
    "turn-in-place",
    "pick-up-object",
    "place-object-down",
    "place-on-object",
    "dock-with-cube",
    "change-block-color"
]

MARKER_DICT = {"Circles2": CustomObjectMarkers.Circles2,
               "Circles3": CustomObjectMarkers.Circles3,
               "Circles4": CustomObjectMarkers.Circles4,
               "Circles5": CustomObjectMarkers.Circles5,
               "Diamonds2": CustomObjectMarkers.Diamonds2,
               "Diamonds3": CustomObjectMarkers.Diamonds3,
               "Diamonds4": CustomObjectMarkers.Diamonds4,
               "Diamonds5": CustomObjectMarkers.Diamonds5,
               "Hexagons2": CustomObjectMarkers.Hexagons2,
               "Hexagons3": CustomObjectMarkers.Hexagons3,
               "Hexagons4": CustomObjectMarkers.Hexagons4,
               "Hexagons5": CustomObjectMarkers.Hexagons5,
               "Triangles2": CustomObjectMarkers.Triangles2,
               "Triangles3": CustomObjectMarkers.Triangles3,
               "Triangles4": CustomObjectMarkers.Triangles4,
               "Triangles5": CustomObjectMarkers.Triangles5}
CUSTOM_OBJECT_TYPES = [CustomObjectTypes.CustomType00,
                       CustomObjectTypes.CustomType01,
                       CustomObjectTypes.CustomType02,
                       CustomObjectTypes.CustomType03,
                       CustomObjectTypes.CustomType04,
                       CustomObjectTypes.CustomType05,
                       CustomObjectTypes.CustomType06,
                       CustomObjectTypes.CustomType07,
                       CustomObjectTypes.CustomType08,
                       CustomObjectTypes.CustomType09,
                       CustomObjectTypes.CustomType10,
                       CustomObjectTypes.CustomType11,
                       CustomObjectTypes.CustomType12,
                       CustomObjectTypes.CustomType13,
                       CustomObjectTypes.CustomType14,
                       CustomObjectTypes.CustomType15,
                       CustomObjectTypes.CustomType16,
                       CustomObjectTypes.CustomType17,
                       CustomObjectTypes.CustomType18,
                       CustomObjectTypes.CustomType19]
CUSTOM_OBJECT_NUM = 0

LIGHT_CUBE_NAMES = {1: "paperclip",
                    2: "lamp",
                    3: "deli*slicer"}

def custom_object_type_factory(type, name):
    global CUSTOM_OBJECT_NUM
    type_name = f"{type}-{name}"
    cozmo_obj_type = _CustomObjectType(type_name, 17 + CUSTOM_OBJECT_NUM)
    CUSTOM_OBJECT_NUM += 1
    return cozmo_obj_type

def obj_distance_factory(obj1, obj2):
    """
    Create a function which calculates the x-y distance between the poses of the two objects.

    Both inputs should be either Cozmo objects or robots and should have a .pose attribute that
    returns a Cozmo Pose object. This function returns another function which, when called, returns
    the current distance (in mm) between the two objects. If one or both  of the objects have a
    pose value of None, the function returns None to signal that failure. If they have different
    origin_ids, the function returns -1 to signal a failure.

    :param obj1: An object that has a .pose attribute
    :param obj2: An object that has a .pose attribute
    :return: Float, distance in mm between obj1 and obj2 according to their poses
    """
    assert hasattr(obj1, "pose"), "Object 1 distance comparison requires .pose attribute"
    assert hasattr(obj2, "pose"), "Object 2 distance comparison requires .pose attribute"

    def obj_distance_calc():
        pose_1 = obj1.pose
        pose_2 = obj2.pose

        if pose_1 is None or pose_2 is None:
            return None

        if pose_1.origin_id != pose_2.origin_id:
            return -1

        x1 = pose_1.position.x
        y1 = pose_1.position.y
        x2 = pose_2.position.x
        y2 = pose_2.position.y

        dist = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        return dist

    return obj_distance_calc


def obj_heading_factory(obj1, obj2):
    """
    Create a function which calculates the relative heading of obj2 from obj1.

    Both inputs should be either Cozmo objects or robots and should have a .pose attribute that
    returns a Cozmo Pose object. This function returns another function which, when called,
    returns the current heading from obj1 to obj2 in degrees, which is how much obj1 would need
    to rotate to face obj2. If one or both have a pose value of None, None is returned. None is
    also returned if the two objects have different origin_ids on their poses.

    :param obj1: An object that has a .pose attribute
    :param obj2: An object that has a .pose attribute
    :return: Float, heading from obj1 to obj2 according to their poses
    """
    assert hasattr(obj1, "pose"), "Object 1 distance comparison requires .pose attribute"
    assert hasattr(obj2, "pose"), "Object 2 distance comparison requires .pose attribute"

    def obj_heading_calc():
        pose_1 = obj1.pose
        pose_2 = obj2.pose

        if pose_1 is None or pose_2 is None:
            return None

        if pose_1.origin_id != pose_2.origin_id:
            return None

        obj1_heading = obj1.pose.rotation.angle_z.degrees

        x2 = pose_2.position.x
        y2 = pose_2.position.y
        obj2_heading = atan2(y2, x2) * 180 / pi

        rel_heading = obj2_heading - obj1_heading
        return rel_heading

    return obj_heading_calc
