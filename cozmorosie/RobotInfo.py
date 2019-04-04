from math import *
from pysoarlib import *

# Info for view region
VIEW_DIST = 4.0
VIEW_ANGLE = pi/2 * 0.7
VIEW_HEIGHT = 1.2

class RobotInfo(WMInterface):
    def __init__(self, world_objs):
        WMInterface.__init__(self)

        self.world_objs = world_objs

        self.self_id = None
        self.wmes = {}

        self.pose_id = None
        self.pose_wmes = [ SoarWME(dim, 0.0) for dim in [ "x", "y", "z", "roll", "pitch", "yaw" ] ]
        self.pose = [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ]
        self.dims = [.5, .2, .3]

        #self.held_object = SoarWME("holding-object", "none")

        self.wm_dirty = False

        self.svs_cmd_queue = []

        self.robot_inputs = {
            "battery-voltage": lambda: self.robot_data.battery_voltage,
            "charging": lambda: int(self.robot_data.is_charging),
            "cliff-detected": lambda: int(self.robot_data.is_cliff_detected),
            "head-angle": lambda: self.robot_data.head_angle.radians,
            "picked-up": lambda: int(self.robot_data.is_picked_up),
            "robot-id": lambda: self.robot_data.robot_id,
            "arm": {
                "carrying-object-id": lambda: str(self.robot_data.carrying_object_id),
                "is-carrying-block": lambda: str(self.robot_data.is_carrying_block),
                "holding-object": lambda: str(self.world_objs.get_soar_handle(str(self.robot_data.carrying_object_id))),
                "angle": lambda: self.robot_data.lift_angle.radians,
                "height": lambda: self.robot_data.lift_height.distance_mm,
                "ratio": lambda: self.robot_data.lift_ratio,
            },
        }

    def update(self, robot_data):
        self.robot_data = robot_data
        yaw = self.robot_data.pose.rotation.angle_z.radians
        pos = self.robot_data.pose.position
        self.pose = [ pos.x/100.0, pos.y/100.0, pos.z/100.0, 0.0, 0.0, yaw ]
        for d, pose_wme in enumerate(self.pose_wmes):
            pose_wme.set_value(self.pose[d])
        self.wm_dirty = True


    def get_svs_commands(self):
        q = self.svs_cmd_queue
        self.svs_cmd_queue = []
        return q

    #################################################
    #
    # HANDLING WORKING MEMORY 
    #
    #################################################

    def _add_to_wm_impl(self, parent_id):
        self.self_id = parent_id.CreateIdWME("self")
        SoarUtils.update_wm_from_tree(self.self_id, "self", self.robot_inputs, self.wmes)

        self.pose_id = self.self_id.CreateIdWME("pose")
        for wme in self.pose_wmes:
            wme.add_to_wm(self.pose_id)

        self.svs_cmd_queue.append("add robot world p {:s} r {:s}\n".format(
            SVSCommands.pos_to_str(self.pose[0:3]), SVSCommands.rot_to_str(self.pose[3:6])))
        self.svs_cmd_queue.append("add robot_pos robot\n")
        self.svs_cmd_queue.append(SVSCommands.add_box("robot_body", parent="robot", scl=self.dims))
        self.svs_cmd_queue.append("add robot_view robot v {:s} p {:f} {:f} {:f}\n".format(
            self._get_view_region_vertices(), VIEW_DIST/2 + 0.5, 0.0, 0.0))

    def _update_wm_impl(self):
        if not self.wm_dirty:
            return

        SoarUtils.update_wm_from_tree(self.self_id, "self", self.robot_inputs, self.wmes)

        for pose_wme in self.pose_wmes:
            pose_wme.update_wm()
        self.svs_cmd_queue.append(SVSCommands.change_pos("robot", self.pose[0:3]))
        self.svs_cmd_queue.append(SVSCommands.change_rot("robot", self.pose[3:6]))

    def _remove_from_wm_impl(self):
        for wme in self.pose_wmes:
            wme.remove_from_wm()
        self.pose_id = None
        SoarUtils.remove_tree_from_wm(self.wmes)
        self.self_id.DestroyWME()
        self.self_id = None

        self.svs_cmd_queue.append("delete robot\n")

    def _get_view_region_vertices(self):
        """ Creates a triangular view region of height VIEW_DIST and angle VIEW_ANGLE """
        verts = []
        dx = VIEW_DIST/2
        dy = VIEW_DIST * sin(VIEW_ANGLE/2)
        dz = VIEW_HEIGHT/2
        # Top triangle
        verts.append("{:f} {:f} {:f}".format(-dx, 0.0, dz))
        verts.append("{:f} {:f} {:f}".format(dx, -dy, dz))
        verts.append("{:f} {:f} {:f}".format(dx, dy, dz))
        # Bottom triangle
        verts.append("{:f} {:f} {:f}".format(-dx, 0.0, -dz))
        verts.append("{:f} {:f} {:f}".format(dx, -dy, -dz))
        verts.append("{:f} {:f} {:f}".format(dx, dy, -dz))

        return " ".join(verts)

