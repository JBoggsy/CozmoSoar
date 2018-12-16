from math import sqrt, atan2, pi

COLORS = ['red', 'blue', 'green', 'white', 'off']


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
    assert hasattr(obj1, 'pose'), "Object 1 distance comparison requires .pose attribute"
    assert hasattr(obj2, 'pose'), "Object 2 distance comparison requires .pose attribute"

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

        dist = sqrt((x2-x1)**2 + (y2-y1)**2)
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
    assert hasattr(obj1, 'pose'), "Object 1 distance comparison requires .pose attribute"
    assert hasattr(obj2, 'pose'), "Object 2 distance comparison requires .pose attribute"

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
