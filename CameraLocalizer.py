

class CameraLocalizer:

    def __init__(self):
        # Spin up a thread to periodically update the transfor
        pass

        # transform
    
    # pose: xyzrpy
    def recalculate_transform(self, pose):
        pass

    # cozmo_pose: xyzrpy
    def get_world_pose(self, cozmo_pose):
        return cozmo_pose

    # world_pose: xyzrpy
    def get_cozmo_pose(self, world_pose):
        return world_pose



