from pysoarlib import *
from math import *

import sys, traceback, re

from threading import Lock
import time

INTERMEDIATE_ACTION_DELAY = 0.15

class RobotDataUnwrapper:
    def __init__(self, world_data):
        self.world = world_data
        self.agent = world_data["agent"]

    def yaw(self):
        # Remapped so yaw=0 is down x-axis and yaw=90 is down y-axis
        return ((450 - int(self.agent["rotation"]["y"])) % 360) * pi / 180.0

    def pos(self):
        p = self.agent["position"]
        return [ p["x"], p["z"], p["y"] ]

    def held_obj(self):
        if len(self.world["inventoryObjects"]) > 0:
            return self.world["inventoryObjects"][0]["objectId"]
        return None

class CommandSyntaxError(Exception):
    pass

class RobotConnector(AgentConnector):
    def __init__(self, agent, sim):
        AgentConnector.__init__(self, agent)
        self.lock = Lock()

        self.sim = sim
        self.sim.add_world_change_listener(lambda world: self.handle_world_change(world))

        self.add_output_command("perform-action")

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

    def handle_world_change(self, world):
        self.lock.acquire()
        unwrapper = RobotDataUnwrapper(world)
        pos = unwrapper.pos()
        yaw = unwrapper.yaw()
        pose = [ pos[0], pos[1], pos[2], 0.0, 0.0, yaw ]
        for d, pose_wme in enumerate(self.pose_wmes):
            pose_wme.set_value(pose[d])

        held_obj = unwrapper.held_obj()
        held_obj_h = self.agent.connectors["perception"].objects.get_soar_handle(held_obj) if held_obj else "none"
        self.held_object.set_value(held_obj_h)

        self.wm_dirty = True
        self.lock.release()

    def on_init_soar(self):
        svs_commands = []
        self.remove_from_wm(svs_commands)
        self.agent.agent.SendSVSInput("\n".join(svs_commands))

    def on_input_phase(self, input_link):
        svs_commands = []
        if not self.added:
            self.lock.acquire()
            self.add_to_wm(input_link, svs_commands)
            self.lock.release()
        elif self.wm_dirty:
            self.lock.acquire()
            self.update_wm(svs_commands)
            self.wm_dirty = False
            self.lock.release()
        if len(svs_commands) > 0:
            self.agent.agent.SendSVSInput("\n".join(svs_commands))

    #################################################
    #
    # HANDLING WORKING MEMORY 
    #
    #################################################

    def add_to_wm(self, parent_id, svs_commands):
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

        self.added = True

    def update_wm(self, svs_commands):
        for pose_wme in self.pose_wmes:
            pose_wme.update_wm()
        self.moving_state.update_wm()
        self.held_object.update_wm()

    def remove_from_wm(self, svs_commands):
        if not self.added:
            return

        self.held_object.remove_from_wm()
        self.arm_id = None

        for wme in self.pose_wmes:
            wme.remove_from_wm()
        self.pose_id = None

        self.moving_state.remove_from_wm()
        self.self_id.DestroyWME()
        self.self_id = None

        #svsCommands.append(String.format("delete robot\n"));
        self.added = False

    #################################################
    #
    # HANDLING SOAR COMMANDS
    #
    ################################################

    def on_output_event(self, command_name, root_id):
        if command_name == "perform-action":
            self.process_perform_action(root_id)

    def process_perform_action(self, root_id):
        try:
            action_name = root_id.GetChildString("name")
            if action_name == None:
                raise CommandSyntaxError("No ^name attribute")

            command = None
            if action_name == "turn":
                command = self.process_turn_command(root_id)
            elif action_name == "drive-forward":
                command = self.process_drive_forward_command(root_id)
            elif action_name == "look":
                command = self.process_look_command(root_id)
            elif action_name == "pick-up":
                command = self.process_pickup_command(root_id)
            elif action_name == "put-down":
                command = self.process_putdown_command(root_id)
            elif action_name == "open":
                command = self.process_open_command(root_id)
            elif action_name == "close":
                command = self.process_close_command(root_id)
            elif action_name == "set-timer":
                command = self.process_set_timer_command(root_id)
            elif action_name == "use":
                command = self.process_use_command(root_id)
            elif action_name == "approach":
                self.perform_approach_command(root_id)
                return
            else:
                raise CommandSyntaxError("Unrecognized Action " + action_name)

            self.sim.exec_command(command)
            time.sleep(INTERMEDIATE_ACTION_DELAY)
            
            root_id.CreateStringWME("status", "success")
        except CommandSyntaxError as e: 
            root_id.CreateStringWME("status", "error")
            root_id.CreateStringWME("error-info", str(e))
        except Exception as e:
            self.print_handler(traceback.format_exc())
            self.print_handler(sys.exc_info())
            root_id.CreateStringWME("status", "error")
            root_id.CreateStringWME("error-info", "runtime error")

    def process_turn_command(self, root_id):
        direction = root_id.GetChildString("direction")
        if direction == None:
            raise CommandSyntaxError("turn is missing ^direction")
        if direction == "right1":
            return { "action":"RotateRight" }
        if direction == "left1":
            return { "action":"RotateLeft" }
        raise CommandSyntaxError("turn given unrecognized direction")

    def process_drive_forward_command(self, root_id):
        return { "action": "MoveAhead" }

    def process_look_command(self, root_id):
        direction = root_id.GetChildString("direction")
        if direction == None:
            raise CommandSyntaxError("look is missing ^direction")
        if direction == "up1":
            return { "action":"LookUp" }
        if direction == "down1":
            return { "action":"LookDown" }
        raise CommandSyntaxError("look given unrecognized direction")

    def process_pickup_command(self, root_id):
        obj_handle = root_id.GetChildString("object")
        if obj_handle == None:
            raise CommandSyntaxError("pick-up is missing ^object")

        perc_id = self.agent.connectors["perception"].objects.get_perception_id(obj_handle)
        if perc_id == None:
            raise CommandSyntaxError("pick-up given unrecognized object " + obj_handle)

        return { "action": "PickupObject", "objectId": perc_id }

    def process_putdown_command(self, root_id):
        obj_handle = root_id.GetChildString("object")
        if obj_handle == None:
            raise CommandSyntaxError("put-down is missing ^object")

        perc_id = self.agent.connectors["perception"].objects.get_perception_id(obj_handle)
        if perc_id == None:
            raise CommandSyntaxError("put-down given unrecognized object " + obj_handle)

        rec_handle = root_id.GetChildString("receptacle")
        if rec_handle == None:
            raise CommandSyntaxError("put-down is missing ^receptacle")

        rec_id = self.agent.connectors["perception"].objects.get_perception_id(rec_handle)
        if rec_id == None:
            raise CommandSyntaxError("put-down given unrecognized receptacle " + rec_handle)

        return { "action": "PutObject", 
                "objectId": perc_id, 
                "receptacleObjectId": rec_id }

    def process_open_command(self, root_id):
        obj_handle = root_id.GetChildString("object")
        if obj_handle == None:
            raise CommandSyntaxError("open is missing ^object")

        perc_id = self.agent.connectors["perception"].objects.get_perception_id(obj_handle)
        if perc_id == None:
            raise CommandSyntaxError("open given unrecognized object " + obj_handle)

        return { "action": "OpenObject", "objectId": perc_id }

    def process_close_command(self, root_id):
        obj_handle = root_id.GetChildString("object")
        if obj_handle == None:
            raise CommandSyntaxError("close is missing ^object")

        perc_id = self.agent.connectors["perception"].objects.get_perception_id(obj_handle)
        if perc_id == None:
            raise CommandSyntaxError("close given unrecognized object " + obj_handle)

        return { "action": "CloseObject", "objectId": perc_id }

    def process_set_timer_command(self, root_id):
        obj_handle = root_id.GetChildString("object")
        if obj_handle == None:
            raise CommandSyntaxError("set-timer is missing ^object")

        perc_id = self.agent.connectors["perception"].objects.get_perception_id(obj_handle)
        if perc_id == None:
            raise CommandSyntaxError("set-timer given unrecognized object " + obj_handle)

        time = root_id.GetChildInt("time")
        if time == None:
            raise CommandSyntaxError("set-timer not given a time")

        return { "action": "SetTime", "objectId": perc_id, "timeset": float(time) }

    def process_use_command(self, root_id):
        obj_handle = root_id.GetChildString("object")
        if obj_handle == None:
            raise CommandSyntaxError("use is missing ^object")

        perc_id = self.agent.connectors["perception"].objects.get_perception_id(obj_handle)
        if perc_id == None:
            raise CommandSyntaxError("use given unrecognized object " + obj_handle)

        tar_handle = root_id.GetChildString("target")
        if tar_handle == None:
            raise CommandSyntaxError("use is missing ^target")

        tar_id = self.agent.connectors["perception"].objects.get_perception_id(tar_handle)
        if tar_id == None:
            raise CommandSyntaxError("use given unrecognized target " + tar_handle)

        return { "action": "UseObject", "toolId": perc_id, "objectId": tar_id }

    def perform_approach_command(self, root_id):
        obj_handle = root_id.GetChildString("object")
        if obj_handle == None:
            raise CommandSyntaxError("approach is missing ^object")

        perc_id = self.agent.connectors["perception"].objects.get_perception_id(obj_handle)
        if perc_id == None:
            raise CommandSyntaxError("approach given unrecognized object " + obj_handle)

        if self.sim.approach_obj(perc_id):
            root_id.CreateStringWME("status", "success")
        else:
            root_id.CreateStringWME("status", "error")
            root_id.CreateStringWME("error-info", "Execution error while doing approach(" + obj_handle + ") " + perc_id)


    # Creates a triangular view region of height VIEW_DIST
    # and angle VIEW_ANGLE and a height of 2m
    #def get_view_region_verts(self):
    #    verts = ""
    #    dx = VIEW_DIST/2
    #    dy = VIEW_DIST * sin(VIEW_ANGLE/2)
    #    dz = VIEW_HEIGHT/2
    #    # Top triangle
    #    # FIX: FORMAT
    #    verts += String.format("%f %f %f ", -dx, 0.0, dz)
    #    verts += String.format("%f %f %f ", dx, -dy, dz)
    #    verts += String.format("%f %f %f ", dx, dy, dz)
    #    # Bottom triangle
    #    verts += String.format("%f %f %f ", -dx, 0.0, -dz)
    #    verts += String.format("%f %f %f ", dx, -dy, -dz)
    #    verts += String.format("%f %f %f", dx, dy, -dz)

    #    return verts

