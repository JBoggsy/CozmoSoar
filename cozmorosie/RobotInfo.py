from pysoarlib import *
from math import *

class RobotDataUnwrapper:
    def __init__(self, robot_data):
        self.data = robot_data

    def yaw(self):
        # Remapped so yaw=0 is down x-axis and yaw=90 is down y-axis
        return ((450 - int(self.data["rotation"]["y"])) % 360) * pi / 180.0

    def pos(self):
        p = self.data["position"]
        return [ p["x"], p["z"], p["y"] ]

    def held_obj(self):
        if len(self.data["inventoryObjects"]) > 0:
            return self.data["inventoryObjects"][0]["objectId"]
        return None

class RobotInfo(WMInterface):
    def __init__(self, agent):
        WMInterface.__init__(self)

        self.self_id = None
        self.arm_id = None
        self.pose_id = None
        self.pose_wmes = []
        for dim in [ "x", "y", "z", "roll", "pitch", "yaw"]:
            self.pose_wmes.append(SoarWME(dim, 0.0))

        self.held_object = SoarWME("holding-object", "none")
        self.moving_state = SoarWME("moving-status", "stopped")

        self.dims = [.5, .5, 1.0]

        self.wm_dirty = False
        self.added = False

        self.svs_cmd_queue = []

    def update(self, robot_data):
        unwrapper = RobotDataUnwrapper(robot_data)
        pos = unwrapper.pos()
        yaw = unwrapper.yaw()
        pose = [ pos[0], pos[1], pos[2], 0.0, 0.0, yaw ]
        for d, pose_wme in enumerate(self.pose_wmes):
            pose_wme.set_value(pose[d])

        held_obj = unwrapper.held_obj()
        held_obj_h = self.agent.connectors["perception"].objects.get_soar_handle(held_obj) if held_obj else "none"
        self.held_object.set_value(held_obj_h)

        self.wm_dirty = True

    #def get_svs_commands(self):
    #    q = self.svs_cmd_queue
    #    self.svs_cmd_queue = []
    #    return q

    #################################################
    #
    # HANDLING WORKING MEMORY 
    #
    #################################################

    def _add_to_wm_impl(self, parent_id):
        self.self_id = parent_id.CreateIdWME("self");
        self.moving_state.add_to_wm(self.self_id)

        self.pose_id = self.self_id.CreateIdWME("pose")
        for wme in self.pose_wmes:
            wme.add_to_wm(self.pose_id)

        self.arm_id = self.self_id.CreateIdWME("arm")
        self.arm_id.CreateStringWME("moving-status", "wait")
        self.held_object.add_to_wm(self.arm_id)
        
        # TODO: Fix SVS 
        #svsCommands.append(String.format("add robot world p %s r %s\n", 
        #        SVSCommands.posToStr(pos), SVSCommands.rotToStr(rot)));
        #svsCommands.append(String.format("add robot_pos robot\n"));
        #svsCommands.append(String.format("add robot_body robot v %s p .2 0 0 s %s\n", 
        #        SVSCommands.bboxVertices(), SVSCommands.scaleToStr(dims)));
        #svsCommands.append(String.format("add robot_view robot v %s p %f %f %f\n", 
        #        getViewRegionVertices(), VIEW_DIST/2 + .5, 0.0, VIEW_HEIGHT/2 - dims[2]/2));

    def _update_wm_impl(self):
        for pose_wme in self.pose_wmes:
            pose_wme.update_wm()
        self.moving_state.update_wm()
        self.held_object.update_wm()

    def _remove_from_wm_impl(self):
        self.held_object.remove_from_wm()
        self.arm_id = None

        for wme in self.pose_wmes:
            wme.remove_from_wm()
        self.pose_id = None

        self.moving_state.remove_from_wm()
        self.self_id.DestroyWME()
        self.self_id = None

        #svsCommands.append(String.format("delete robot\n"));

