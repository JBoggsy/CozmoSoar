from time import sleep
from math import pi

import pysoarlib as psl
import Python_sml_ClientInterface as sml

import cozmo
from cozmo.util import radians, degrees, distance_mm, speed_mmps
from CameraLocalizer import CameraLocalizer

from c_soar_util import *

from cozmorosie.WorldObjectManager import WorldObjectManager
from cozmorosie.RobotInfo import RobotInfo
from cozmorosie.CustomWalls import define_custom_walls, define_custom_cubes

deg2rad = lambda d: d*pi/180.0
rad2deg = lambda r: r/pi*180.0

import time
current_time_ms = lambda: int(round(time.time() * 1000))


class CozmoSoar(psl.AgentConnector):
    """
    A class representing the Soar interface with a Cozmo robot.

    The `CozmoSoar`class is a concrete instantiation of the `AgentConnector` class from Aaron
    Mininger's pysoarlib, which provides a way to connect with a running Soar kernel in Python
    with callbacks. The purpose of the `CozmoSoar` class is to provide a custom way to connect
    the Cozmo robot with Soar by updating the appropriate input link attributes and interpreting
    the resulting output link commands.
    """

    def __init__(self, agent: psl.SoarAgent, robot: cozmo.robot):
        """
        Create an instance of the `CozmoSoar` class connecting the agent to the robot.

        :param agent: The `SoarAgent` object which represents the agent which should control this
                      Cozmo.
        :param robot: The Cozmo `robot` instance representing the Cozmo robot being controlled.
        """
        super(CozmoSoar, self).__init__(agent)
        self.name = self.agent.agent_name
        self.robot = self.r = robot
        self.world = self.w = self.r.world
        self.localizer = CameraLocalizer()
        self.last_cam_update = 0

        self.cam = self.r.camera
        self.cam.image_stream_enabled = True
        self.r.enable_facial_expression_estimation()

        self.world_objs = WorldObjectManager()
        self.robot_info = RobotInfo(self.world_objs, agent.settings.get("map_info_file"))
        self.faces = {}
        self.actions = []

        define_custom_walls(self.world)
        define_custom_cubes(self.world)


        #######################
        # Working Memory data #
        #######################

        # self.static_inputs maps each static input to a function to retrieve its latest value from
        #   Soar. A static input is one that won't ever disappear, in contrast to temporary inputs
        #   like faces or objects
        self.static_inputs = {
            "face-count": self.w.visible_face_count,
            "object-count": lambda: len(self.world_objs.objects),
            "serial": lambda: self.r.serial,
        }

        # self.WMEs maps SoarWME objects to their attribute names for easier retrieval. Since Cozmo
        #   inputs will always be one-to-one with their values (i.e., there won't be multiple values
        #   with the same name), a standard dictionary is fine
        self.WMEs = {}

        ###############################
        # Command Handling dictionary #
        ###############################
        self.command_map = {
            "move-lift": self.__handle_move_lift,
            "go-to-object": self.__handle_go_to_object,
            "go-to-pose": self.__handle_go_to_pose,
            "move-head": self.__handle_move_head,
            "turn-to-face": self.__handle_turn_to_face,
            "turn-to-object": self.__handle_turn_to_object,
            "set-backpack-lights": self.__handle_set_backpack_lights,
            "drive-forward": self.__handle_drive_forward,
            "turn-in-place": self.__handle_turn_in_place,
            "pick-up-object": self.__handle_pick_up_object,
            "place-object-down": self.__handle_place_object_down,
            "place-on-object": self.__handle_place_on_object,
            "dock-with-cube": self.__handle_dock_with_cube,
            "pop-a-wheelie": self.__handle_pop_a_wheelie,
            "roll-cube": self.__handle_roll_cube,
            "change-block-color": self.__handle_change_block_color,
            "stop": self.__handle_stop,
        }

    def on_output_event(self, command_name: str, root_id: sml.Identifier):
        """
        Handle commands Soar outputs by initiating the appropriate Soar action.

        Currently, all this does is use a dictionary mapping from the command name to the
        appropriate handling function.

        :param command_name: Name of the command being issued
        :param root_id: sml Identifier object containing the command
        :return: None
        """
        #print(
        #    "!!! A: ",
        #    command_name,
        #    [root_id.GetChild(c) for c in range(root_id.GetNumberChildren())],
        #)
        action, status_wme = self.command_map[command_name](root_id)
        if action:
            print(action)
            self.actions.append((action, status_wme, root_id))
        #else:
        #    print("Output Command " + command_name + " had a syntax error")
        #    root_id.CreateStringWME("status", "error")

    def on_init_soar(self):
        self.world_objs.remove_from_wm()
        self.robot_info.remove_from_wm()

        svs_commands = self.world_objs.get_svs_commands()
        svs_commands.extend(self.robot_info.get_svs_commands())
        if len(svs_commands) > 0:
            self.agent.agent.SendSVSInput("\n".join(svs_commands))

        psl.SoarUtils.remove_tree_from_wm(self.WMEs)
        self.actions = []

    def __handle_stop(self, command: sml.Identifier):
        """
        Will stop the current action

        The Sour output should look like:
        (I3 ^stop <stop>)
        Cozmo should stop the current action

        :return: True if successful, False otherwise
        """
        print("STOPPING")
        self.robot.abort_all_actions()
        status_wme = psl.SoarWME("status", "complete")
        status_wme.add_to_wm(command)

        return (None, None)


    def __handle_place_object_down(self, command: sml.Identifier):
        """
        Handle a Soar place-object-down action.

        The Sour output should look like:
        (I3 ^place-object-down)
        Cozmo will lower the lift until the object is placed on the ground, then back up.

        :param command: Soar command object
        :return: True if successful, False otherwise
        """
        print("Placing object down")
        place_object_down_action = self.r.place_object_on_ground_here(0, in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return place_object_down_action, status_wme

    def __handle_place_on_object(self, command: sml.Identifier):
        """
        Handle a Soar place-on-object action.

        The Sour output should look like:
        (I3 ^place-on-object Vx)
          (Vx ^object-id [id])
        where [id] is the object id of the object that Cozmo should place to object its holding
        on top of.

        :param command: Soar command object
        :return: True if successful, False otherwise
        """

        target_id = command.GetParameterValue("object-id")
        target_obj = self.world_objs.get_object(target_id)
        if not target_obj:
            print("Couldn't find target object: {}".format(target_id))
            print(self.world_objs)
            return False

        print("Placing held object on top of {}".format(target_id))
        place_on_object_action = self.robot.place_on_object(target_obj.cozmo_obj, in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return place_on_object_action, status_wme

    def __handle_dock_with_cube(self, command: sml.Identifier):
        """
        Handle a Soar dock-with-cube action.

        The Sour output should look like:
        (I3 ^dock-with-cube Vx)
          (Vx ^object-id [id])
        where [id] is the object id of the cube to dock with. Cozmo will approach the cube until
        its lift hooks are under the grip holes.

        :param command: Soar command object
        :return: True if successful, False otherwise
        """

        target_id = command.GetParameterValue("object-id")
        target_obj = self.world_objs.get_object(target_id)
        if not target_obj:
            print("Couldn't find target object: {}".format(target_id))
            print(self.world_objs)
            return False

        print("Docking with cube with object id {}".format(target_id))
        dock_with_cube_action = self.robot.dock_with_cube(target_obj.cozmo_obj, in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return dock_with_cube_action, status_wme

    def __handle_pick_up_object(self, command: sml.Identifier):
        """
        Handle a Soar pick-up-object action.

        The Sour output should look like:
        (I3 ^pick-up-object Vx)
          (Vx ^object-id [id])
        where [id] is the object id of the object to pick up. Cozmo will approach the object
        autonomously and try to grasp it with its lift, then lift the lift up. This action is
        partiularly prone to failing.

        :param command: Soar command object
        :return: True if successful, False otherwise
        """

        target_id = command.GetParameterValue("object-id")
        target_obj = self.world_objs.get_object(target_id)
        if not target_obj:
            print("Couldn't find target object: {}".format(target_id))
            print(self.world_objs)
            return False

        print("Picking up object {}".format(target_id))
        pick_up_object_action = self.robot.pickup_object(target_obj.cozmo_obj, in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return pick_up_object_action, status_wme

    def __handle_turn_to_face(self, command: sml.Identifier):
        """
        Handle a Soar turn-to-face action.

        The Soar output should look like:
        (I3 ^turn-to-face Vx)
          (Vx ^face-id [fid])
        where [fid] is the integer ID associated with the face to turn towards.

        :param command: Soar command object
        :return: True if successful, False otherwise
        """
        try:
            fid = int(command.GetParameterValue("face-id"))
        except ValueError as e:
            print("Invalid face id format {}".format(command.GetParameterValue("face-id")))
            return False
        if fid not in self.faces.keys():
            print("Face {} not recognized".format(fid))
            return False

        print("Turning to face {}".format(fid))
        target_face = self.faces[fid]
        turn_towards_face_action = self.r.turn_towards_face(target_face, in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return turn_towards_face_action, status_wme

    def __handle_turn_to_object(self, command: sml.Identifier):
        """
        Handle a Soar turn-to-object action.

        The Sour output should look like:
        (I3 ^turn-to-object Vx)
          (Vx ^object-id [id])
        where [id] is the object id of the object to face towards. 
        Cozmo will turn to face the object. 

        :param command: Soar command object
        :return: True if successful, False otherwise
        """

        target_id = command.GetParameterValue("object-id")
        target_obj = self.world_objs.get_object(target_id)
        if not target_obj:
            print("Couldn't find target object: {}".format(target_id))
            print(self.world_objs)
            return False


        print("Turning to face {}".format(target_id))
        turn_towards_object_action = self.r.turn_towards_object(target_obj.cozmo_obj, in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return turn_towards_object_action, status_wme


    def __handle_move_lift(self, command: sml.Identifier):
        """
        Handle a Soar move-lift action.

        The Soar output should look like:
        (I3 ^move-lift Vx)
          (Vx ^height [hgt])
        where [hgt] is a real number in the range [0, 1]. This command moves the lift to the
        the given height, where 0 is the lowest possible position and 1 is the highest.

        :param command: Soar command object
        :return: True if successful, False otherwise
        """
        try:
            height = float(command.GetParameterValue("height"))
        except ValueError as e:
            print("Invalid height format {}".format(command.GetParameterValue("height")))
            return False

        print("Moving lift {}".format(height))
        set_lift_height_action = self.robot.set_lift_height(height, in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return set_lift_height_action, status_wme

    def __handle_move_head(self, command: sml.Identifier):
        """
        Handle a Soar move-head action.

        The Soar output should look like:
        (I3 ^move-head Vx)
          (Vx ^angle [ang])
        where [ang] is a real number in the range [-0.44, 0.78]. This command moves the head to the
        the given angle, where 0 is looking straight ahead and the angle is radians from that
        position.

        :param command: Soar command object
        :return: True if successful, False otherwise
        """
        try:
            angle = float(command.GetParameterValue("angle"))
        except ValueError as e:
            print("Invalid angle format {}".format(command.GetParameterValue("angle")))
            return False

        print("Moving head {}".format(angle))
        set_head_angle_action = self.robot.set_head_angle(radians(angle), in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return set_head_angle_action, status_wme

    def __handle_go_to_object(self, command: sml.Identifier):
        """
        Handle a Soar go-to-object action.

        The Sour output should look like:
        (I3 ^go-to-object Vx)
          (Vx ^object-id [id])
        where [id] is the object id of the object to go to. Cozmo will stop 150mm from the object.

        :param command: Soar command object
        :return: True if successful, False otherwise
        """

        target_id = command.GetParameterValue("object-id")
        target_obj = self.world_objs.get_object(target_id)
        if not target_obj:
            print("Couldn't find target object: {}".format(target_id))
            print(self.world_objs)
            return False

        print("Going to object {}".format(target_id))
        go_to_object_action = self.robot.go_to_object(target_obj.cozmo_obj, distance_mm(1000), in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return go_to_object_action, status_wme

    def __handle_go_to_pose(self, command: sml.Identifier):
        """
        Handle a Soar go-to-pose action.

        The Sour output should look like:
        (I3 ^go-to-pose Vx)
          (Vx ^x <x> ^y <y> ^orientation <orient> ^relative << true false >> )

        where x and y are floats representing coordinates in meters
        and orient is a float representing heading in degrees
        relative is an optional Boolean, if True then the pose will be relative to the robot

        :param command: Soar command object
        :return: True if successful, False otherwise
        """

        x = command.GetChildFloat("x")
        y = command.GetChildFloat("y")
        orient = command.GetChildFloat("orientation")

        if x == None or y == None or orient == None:
            print("go-to-pose requires x, y, and orientation")
            return False

        pose = cozmo.util.pose_z_angle(x=x*1000, y=y*1000, z=0.0, angle_z=radians(orient))

        relative = command.GetChildString("relative")
        relative = (relative != None and relative.lower() == "true")

        if not relative:
            world_pose = self.localizer.get_world_pose([x, y, 0.0, 0.0, 0.0, orient])
            pose = cozmo.util.pose_z_angle(x=world_pose[0]*1000, y=world_pose[1]*1000, z=0.0, angle_z=radians(world_pose[5]))

        print("Going to ({}, {}) with orientation {}, relative={}".format(x, y, orient, relative))
        go_to_pose_action = self.robot.go_to_pose(pose, relative_to_robot=relative, in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return go_to_pose_action, status_wme

    def __handle_set_backpack_lights(self, command: sml.Identifier):
        """
        Handle a Soar set-backpack-lights action.

        The Sour output should look like:
        (I3 ^set-backpack-lights Vx)
          (Vx ^color [color])
        where [color] is a string indicating which color the lights should be set to. The colors
        are "red", "blue", "green", "white", and "off".

        :param command: Soar command object
        :return: True if successful, False otherwise
        """
        color_str = command.GetParameterValue("color")
        if color_str not in COLORS:
            print("Invalid backpack lights color {}".format(color_str))
            return False
        elif color_str == "red":
            light = cozmo.lights.red_light
        elif color_str == "green":
            light = cozmo.lights.green_light
        elif color_str == "blue":
            light = cozmo.lights.blue_light
        elif color_str == "white":
            light = cozmo.lights.white_light
        else:
            light = cozmo.lights.off_light

        self.r.set_all_backpack_lights(light=light)
        command.AddStatusComplete()
        return (None, None)

    def __handle_drive_forward(self, command: sml.Identifier):
        """
        Handle a Soar drive-forward action.

        The Sour output should look like:
        (I3 ^drive-forward Vx)
          (Vx ^distance [dist]
              ^speed [spd])
        where [dist] is a real number indicating how far Cozmo should travel (negatives go
        backwards) and speed is how fast Cozmo should travel. Units are meter and meter/sec, respectively.

        :param command: Soar command object
        :return: True if successful, False otherwise
        """
        try:
            distance = distance_mm(float(command.GetParameterValue("distance"))*1000)
        except ValueError as e:
            print("Invalid distance format {}".format(command.GetParameterValue("distance")))
            return False
        try:
            speed = speed_mmps(float(command.GetParameterValue("speed"))*1000)
        except ValueError as e:
            print("Invalid speed format {}".format(command.GetParameterValue("speed")))
            return False

        print("Driving forward {}mm at {}mm/s".format(distance.distance_mm, speed.speed_mmps))
        drive_forward_action = self.r.drive_straight(distance, speed, in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return drive_forward_action, status_wme

    def __handle_turn_in_place(self, command: sml.Identifier):
        """
        Handle a Soar turn-in-place action.

        The Sour output should look like:
        (I3 ^turn-in-place Vx)
          (Vx ^angle [ang]
              ^speed [spd]
              ^absolute << true false >>)
        where [ang] is the amount Cozmo should rotate in radians and speed is the speed at which
        Cozmo should rotate in rad/s. 
        If absolute=true, the angle is an absolute angle (turn to face angle theta)
            This is optional and defaults to false

        :param command: Soar command object
        :return: True if successful, False otherwise
        """
        try:
            angle = float(command.GetParameterValue("angle"))
        except ValueError as e:
            print("Invalid angle format {}".format(command.GetParameterValue("angle")))
            return False
        try:
            speed = float(command.GetParameterValue("speed"))
        except ValueError as e:
            print("Invalid speed format {}".format(command.GetParameterValue("speed")))
            return False

        absolute = command.GetChildString("absolute")
        absolute = (absolute == "true" or absolute == "True")
        if absolute:
            angle = self.localizer.get_world_pose([0.0, 0.0, 0.0, 0.0, 0.0, angle])[5]

        print("Rotating in place {} degrees at {}deg/s".format(angle, speed))
        turn_in_place_action = self.r.turn_in_place(angle=radians(angle), speed=radians(speed), is_absolute=absolute, in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return turn_in_place_action, status_wme

    def __handle_roll_cube(self, command: sml.Identifier):
        """
        Handle a Soar roll-cube action.

        The Sour output should look like:
        (I3 ^roll-cube Vx)
          (Vx ^object-id [id])
        where [id] is the object id of the cube to roll (must be a light cube).
        Cozmo will attempt to rotate the cube by one face

        :param command: Soar command object
        :return: True if successful, False otherwise
        """

        target_id = command.GetParameterValue("object-id")
        target_obj = self.world_objs.get_object(target_id)
        if not target_obj:
            print("Couldn't find target object: {}".format(target_id))
            print(self.world_objs)
            return False

        print("Rolling object {}".format(target_id))
        roll_cube_action = self.robot.roll_cube(target_obj.cozmo_obj, in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return roll_cube_action, status_wme

    def __handle_pop_a_wheelie(self, command: sml.Identifier):
        """
        Handle a Soar pop-a-wheelie action.

        The Sour output should look like:
        (I3 ^pop-a-wheelie Vx)
          (Vx ^object-id [id])
        where [id] is the object id of the cube to use to help it do a wheelie. (must be a light cube).

        :param command: Soar command object
        :return: True if successful, False otherwise
        """

        target_id = command.GetParameterValue("object-id")
        target_obj = self.world_objs.get_object(target_id)
        if not target_obj:
            print("Couldn't find target object: {}".format(target_id))
            print(self.world_objs)
            return False

        print("Rolling object {}".format(target_id))
        wheelie_action = self.robot.pop_a_wheelie(target_obj.cozmo_obj, in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return wheelie_action, status_wme

    def __handle_change_block_color(self, command: sml.Identifier):
        """
        Handle a Soar change-block-color command.
        The Soar output should look like:
        (I3 ^change-block-color Vx)
            (Vx ^color [red, blue, green, white, off]
                ^object-id [id])
        where id is the object-id of the cube which should have its color
        changed.
        :param command: Soar command object
        :return: True if successful, False otherwise
        """

        target_id = command.GetParameterValue("object-id")
        target_obj = self.world_objs.get_object(target_id)
        if not target_obj:
            print("Couldn't find target object: {}".format(target_id))
            print(self.world_objs)
            return False

        color = command.GetParameterValue("color").lower()
        if color not in COLORS:
            print("Invalid color choice: {}".format(color))
            status_wme = psl.SoarWME("status", "failed")
            fail_code_wme = psl.SoarWME("failure-code", "invalid-color")
            fail_reason_wme = psl.SoarWME("failure-reason", "invalid-color: {}".format(color))
            status_wme.add_to_wm(command)
            fail_code_wme.add_to_wm(command)
            fail_reason_wme.add_to_wm(command)
            status_wme.update_wm()
            return False

        print("Changing object {} to color {}".format(target_id, color))
        target_obj.cozmo_obj.set_lights(LIGHTS_DICT[color])
        target_obj.properties["color"].set_value(color)
        status_wme = psl.SoarWME("status", "complete")
        status_wme.add_to_wm(command)
        status_wme.update_wm()
        return (None, None)


    def on_input_phase(self, input_link: sml.Identifier):
        """
        Prior to each input phase, update the changed values of Soar's input link

        Scan through the designated Cozmo inputs and update the corresponding WMEs in Soar via
        instances of the `SoarWME` class. For each input, we first get the value, then check
        whether there exists a WME with that attribute name. If not, we add one to the Soar agent
        and the WME dict of the `CozmoSoar` object. Otherwise, we retrieve the `SoarWME` object
        associated with the input and update its value, then call its `update_wm` method. For
        terminal WMEs, this is simple. However, for sub-trees we need to recursively update
        the WMEs.

        We have to handle temporary inputs e.g., faces or objects, differently, because they
        need to be removed when they are no longer detected.

        :param input_link: The Soar WME corresponding to the input link of the agent.
        :return: None
        """
        psl.SoarUtils.update_wm_from_tree(input_link, "", self.static_inputs, self.WMEs)

        #####################################################
        # UPDATE ROBOT INFORMATION 
        #####################################################

        if current_time_ms() - self.last_cam_update > LOCALIZER_UPDATE_RATE:
            yaw = self.robot_data.pose.rotation.angle_z.radians
            pos = self.robot_data.pose.position
            self.localizer.recalculate_transform([ pos.x/1000.0, pos.y/1000.0, pos.z/1000.0, 0.0, 0.0, yaw ])
            self.last_cam_update = current_time_ms()

        self.robot_info.update(self.r, self.localizer)
        self.robot_info.update_wm(input_link)
        svs_commands = self.robot_info.get_svs_commands()
        if len(svs_commands) > 0:
            self.agent.agent.SendSVSInput("\n".join(svs_commands))

        ## First, we handle inputs which will always be present
        #for input_name in self.static_inputs.keys():
        #    new_val = self.static_inputs[input_name]
        #    wme = self.WMEs.get(input_name)

        #    if not callable(new_val):
        #        if wme is None:
        #            wme = input_link.CreateIdWME(input_name)
        #            self.WMEs[input_name] = wme
        #        self.__input_recurse(new_val, input_name, wme)
        #        continue

        #    new_val = new_val()
        #    if wme is None:
        #        new_wme = psl.SoarWME(att=input_name, val=new_val)
        #        self.WMEs[input_name] = new_wme
        #        new_wme.add_to_wm(input_link)
        #    else:
        #        wme.set_value(new_val)
        #        wme.update_wm()

        # Then, check through the visible faces and objects to see if they need to be added,
        # updated, or removed
        #######################
        # FACE INPUT HANDLING #
        #######################
        vis_faces = set(list(self.w.visible_faces))
        for face in vis_faces:
            face_designation = "face{}".format(face.face_id)
            if face_designation in self.faces:
                face_wme = self.WMEs[face_designation]
            else:
                self.faces[face_designation] = face
                face_wme = input_link.CreateIdWME("face")
                self.WMEs[face_designation] = face_wme
            self.__build_face_wme_subtree(face, face_designation, face_wme)

        faces_missing = set()
        for face_dsg in self.faces.keys():
            if self.faces[face_dsg] not in vis_faces:
                faces_missing.add(face_dsg)
        for face_dsg in faces_missing:
            del self.faces[face_dsg]
            remove_list = [(n, self.WMEs[n]) for n in self.WMEs.keys() if n.startswith(face_dsg)]
            remove_list = sorted(remove_list, key=lambda s: 1/len(s[0]))
            for wme_name, wme in remove_list:
                del self.WMEs[wme_name]
                if isinstance(wme, psl.SoarWME):
                    wme.remove_from_wm()
                elif isinstance(wme, sml.Identifier):
                    wme.DestroyWME()
                else:
                    raise Exception("WME wasn't of proper type")


        #########################
        # OBJECT INPUT HANDLING #
        #########################
        self.world_objs.update(list(self.w.visible_objects), self.localizer)
        self.world_objs.update_wm(input_link)
        svs_commands = self.world_objs.get_svs_commands()
        if len(svs_commands) > 0:
            self.agent.agent.SendSVSInput("\n".join(svs_commands))


#
        # Finally, we want to check all our on-going actions and handle them appropriately:
        # Actions are by default on the output link and have a `status` attribute already,
        # we just need to update that status if needed
        for action, status_wme, root_id in self.actions:
            if action.is_completed:
                state = "succeeded" if action.has_succeeded else "failed"
                failure_reason = action.failure_reason

                status_wme.set_value(state)
                if failure_reason != (None, None):
                    code_wme = psl.SoarWME("failure-code", failure_reason[0])
                    reason_wme = psl.SoarWME("failure-reason", failure_reason[1])
                    code_wme.add_to_wm(root_id)
                    code_wme.update_wm()
                    reason_wme.add_to_wm(root_id)
                    reason_wme.update_wm()
                status_wme.update_wm()
                self.actions.remove((action, status_wme, root_id))



    def __build_face_wme_subtree(self, face, face_designation, face_wme):
        """
        Build a working memory sub-tree for a given perceived face

        :param face: Cozmo faces.Face object to put into working memory
        :param face_designation: Unique string name of the face
        :param face_wme: sml identifier at the root of the face sub-tree
        :return: None
        """
        face_input_dict = {
            "expression": lambda: face.expression,
            "exp-score": lambda: face.expression_score,
            "face-id": lambda: face.face_id,
            "name": lambda: face.name if face.name != "" else "unknown",
            "pose": {
                "rot": lambda: face.pose.rotation.angle_z.degrees,
                "x": lambda: face.pose.position.x,
                "y": lambda: face.pose.position.y,
                "z": lambda: face.pose.position.z,
            }
        }

        psl.SoarUtils.update_wm_from_tree(face_wme, face_designation, face_input_dict, self.WMEs)


class SoarObserver(psl.AgentConnector):
    """
    An `AgentConnector` subclass for viewing infromation about the Soar agent.

    This class just exists to handle getting information out of Soar and into a useful format.
    """

    def __init__(self, agent: psl.SoarAgent, print_handler=None):
        super(SoarObserver, self).__init__(agent, print_handler)

    def on_input_phase(self, input_link):
        print("State:")
        self.agent.execute_command("print --depth 2 s1")
        print("Input link:")
        self.agent.execute_command("print --depth 3 i2")
        print("Output link:")
        self.agent.execute_command("print --depth 4 i3")
