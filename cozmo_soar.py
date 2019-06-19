from time import sleep, time
import xml.etree.ElementTree as ET

import PySoarLib as psl
import soar.Python_sml_ClientInterface as sml
import navmap_utils as nu

import cozmo
from cozmo.util import degrees, distance_mm, speed_mmps
from c_soar_util import *


class CozmoSoar(psl.AgentConnector):
    """
    A class representing the Soar interface with a Cozmo robot.

    The `CozmoSoar`class is a concrete instantiation of the `AgentConnector` class from Aaron
    Mininger's PySoarLib, which provides a way to connect with a running Soar kernel in Python
    with callbacks. The purpose of the `CozmoSoar` class is to provide a custom way to connect
    the Cozmo robot with Soar by updating the appropriate input link attributes and interpreting
    the resulting output link commands.
    """
    def __init__(self, agent: psl.SoarAgent, robot: cozmo.robot, object_file=None):
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
        if object_file:
            self.custom_objects = define_custom_objects_from_file(self.world, object_file)

        self.start_time = time()

        self.cam = self.r.camera
        self.cam.image_stream_enabled = True
        self.r.enable_facial_expression_estimation()

        self.objects = {}
        self.faces = {}
        self.actions = []
        self.w.request_nav_memory_map(.5)
        self.svs_buffer = {}
    
        #######################
        # Working Memory data #
        #######################

        # self.static_inputs maps each static input to a function to retrieve its latest value from
        #   Soar. A static input is one that won't ever disappear, in contrast to temporary inputs
        #   like faces or objects
        self.static_inputs = {
            "battery-voltage": lambda: self.r.battery_voltage,
            "carrying-block": lambda: int(self.r.is_carrying_block),
            "carrying-object-id": lambda: self.r.carrying_object_id,
            "charging": lambda: int(self.r.is_charging),
            "cliff-detected": lambda: int(self.r.is_cliff_detected),
            "head-angle": lambda: self.r.head_angle.degrees,
            "face-count": self.w.visible_face_count,
            "object-count": lambda: len(self.objects),
            "picked-up": lambda: int(self.r.is_picked_up),
            "robot-id": lambda: self.r.robot_id,
            "serial": lambda: self.r.serial,
            "pose": {
                "rot": lambda: self.r.pose.rotation.angle_z.degrees,
                "x": lambda: self.r.pose.position.x,
                "y": lambda: self.r.pose.position.y,
                "z": lambda: self.r.pose.position.z,
            },
            "lift": {
                "angle": lambda: self.r.lift_angle.degrees,
                "height": lambda: self.r.lift_height.distance_mm,
                "ratio": lambda: self.r.lift_ratio,
            },
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
            "move-head": self.__handle_move_head,
            "go-to-object": self.__handle_go_to_object,
            "turn-to-face": self.__handle_turn_to_face,
            "drive-forward": self.__handle_drive_forward,
            "turn-in-place": self.__handle_turn_in_place,
            "pick-up-object": self.__handle_pick_up_object,
            "dock-with-cube": self.__handle_dock_with_cube,
            "place-on-object": self.__handle_place_on_object,
            "place-object-down": self.__handle_place_object_down,
            "change-block-color": self.__handle_change_block_color,
            "set-backpack-lights": self.__handle_set_backpack_lights
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
        print(
            "!!! A: ",
            command_name,
            [root_id.GetChild(c) for c in range(root_id.GetNumberChildren())],
        )
        results = self.command_map[command_name](root_id)
        if not results:
            print("Error execcuting command")
        else:
            action, status_wme = results
            # print(action)
            self.actions.append((action, status_wme, root_id))

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
        try:
            target_id = int(command.GetParameterValue("object-id"))
        except ValueError as e:
            print(
                "Invalid object-id format {}".format(
                    command.GetParameterValue("object-id")
                )
            )
            return False

        target_dsg = "obj{}".format(target_id)
        if target_dsg not in self.objects.keys():
            print("Couldn't find target object")
            print(self.objects)
            return False

        print("Placing held object on top of {}".format(target_dsg))
        target_obj = self.objects[target_dsg]
        place_on_object_action = self.robot.place_on_object(target_obj, in_parallel=True)
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
        try:
            target_id = int(command.GetParameterValue("object-id"))
            target_id = "obj{}".format(target_id)
        except ValueError as e:
            print(
                "Invalid target-object-id format {}".format(command.GetParameterValue("object-id"))
            )
            return False
        if target_id not in self.objects.keys():
            print("Couldn't find target object")
            return False

        print("Docking with cube with object id {}".format(target_id))
        target_obj = self.objects[target_id]
        dock_with_cube_action = self.robot.dock_with_cube(target_obj, in_parallel=True)
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
        try:
            target_id = int(command.GetParameterValue("object-id"))
        except ValueError as e:
            print("Invalid object-id format {}".format(command.GetParameterValue("object-id")))
            return False

        obj_designation = "obj{}".format(target_id)
        if not self.objects.get(obj_designation):
            print("Couldn't find target object")
            return False

        print("Picking up object {}".format(obj_designation))
        target_obj = self.objects[obj_designation]
        pick_up_object_action = self.robot.pickup_object(target_obj, in_parallel=True)
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
        the given angle, where 0 is looking straight ahead and the angle is degrees from that
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
        set_head_angle_action = self.robot.set_head_angle(degrees(angle), in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return set_head_angle_action, status_wme

    def __handle_go_to_object(self, command: sml.Identifier):
        """
        Handle a Soar go-to-object action.

        The Sour output should look like:
        (I3 ^go-to-object Vx)
          (Vx ^object-id [id]
              ^distance [dist])
        where [id] is the object id of the object to go to and [dist] indicates
        how far to stop from the object in mm. Only works on LightCubes.

        :param command: Soar command object
        :return: True if successful, False otherwise
        """
        try:
            target_id = int(command.GetParameterValue("object-id"))
            target_id = f"obj{target_id}"
        except ValueError as e:
            print(
                "Invalid target-object-id format {}".format(
                    command.GetParameterValue("object-id")
                )
            )
            return False
        if target_id not in self.objects.keys():
            print("Couldn't find target object")
            return False

        try:
            distance = distance_mm(float(command.GetParameterValue("distance")))
        except ValueError as e:
            print("Invalid distance format {}".format(command.GetParameterValue("distance")))
            return False

        print("Going to object {}".format(target_id))
        target_obj = self.objects[target_id]
        go_to_object_action = self.robot.go_to_object(target_obj, distance, in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return go_to_object_action, status_wme

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
        backwards) and speed is how fast Cozmo should travel. Units are mm and mm/s, respectively.

        :param command: Soar command object
        :return: True if successful, False otherwise
        """
        try:
            distance = distance_mm(float(command.GetParameterValue("distance")))
        except ValueError as e:
            print("Invalid distance format {}".format(command.GetParameterValue("distance")))
            return False
        try:
            speed = speed_mmps(float(command.GetParameterValue("speed")))
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
              ^speed [spd])
        where [ang] is the amount Cozmo should rotate in degrees and speed is the speed at which
        Cozmo should rotate in deg/s.

        :param command: Soar command object
        :return: True if successful, False otherwise
        """
        try:
            angle = degrees(float(command.GetParameterValue("angle")))
        except ValueError as e:
            print("Invalid angle format {}".format(command.GetParameterValue("angle")))
            return False
        try:
            speed = degrees(float(command.GetParameterValue("speed")))
        except ValueError as e:
            print("Invalid speed format {}".format(command.GetParameterValue("speed")))
            return False

        print("Rotating in place {} degrees at {}deg/s".format(angle.degrees, speed.degrees))
        turn_in_place_action = self.r.turn_in_place(angle=angle, speed=speed, in_parallel=True)
        status_wme = psl.SoarWME("status", "running")
        status_wme.add_to_wm(command)
        status_wme.update_wm()

        return turn_in_place_action, status_wme

    def __handle_change_block_color(self, command: sml.Identifier):
        """
        Handle a Soar change-block-color command.

        The Soar output should look like:
        (I3 ^change-block-color Vx)
            (Vx ^color [str]
                ^object-id [id])
        where color is the color name to change to from the valid colors and id
        is the object-id of the cube which should have its color changed.

        :param command: Soar command object
        :return: True if successful, False otherwise
        """
        try:
            target_id = int(command.GetParameterValue("object-id"))
        except ValueError as e:
            #TODO: Update action WME to have failure codes
            print("Invalid object-id format, must be int")
            return False
        if f"obj{target_id}" not in self.objects.keys():
            #TODO: Update action WME to have failure codes
            print(f"Invalid object-id {target_id}, can't find it")
            return False

        color = command.GetParameterValue("color").lower()
        if color not in COLORS:
            print(f"Invalid color choice: {color}")
            status_wme = psl.SoarWME("status", "failed")
            fail_code_wme = psl.SoarWME("failure-code", "invalid-color")
            fail_reason_wme = psl.SoarWME("failure-reason", "invalid-color: {}".format(color))
            status_wme.add_to_wm(command)
            fail_code_wme.add_to_wm(command)
            fail_reason_wme.add_to_wm(command)
            status_wme.update_wm()
            return False

        print(f"Changing object {target_id} to color {color}")
        target_block = self.objects[f"obj{target_id}"]
        print("Target object: {}".format(target_block.cube_id))
        target_block.set_lights_off()
        target_block.set_lights(LIGHTS_DICT[color])
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
        # First, we handle inputs which will always be present
        for input_name in self.static_inputs.keys():
            new_val = self.static_inputs[input_name]
            wme = self.WMEs.get(input_name)

            if not callable(new_val):
                if wme is None:
                    wme = input_link.CreateIdWME(input_name)
                    self.WMEs[input_name] = wme
                self.__input_recurse(new_val, input_name, wme)
                continue

            new_val = new_val()
            if wme is None:
                new_wme = psl.SoarWME(att=input_name, val=new_val)
                self.WMEs[input_name] = new_wme
                new_wme.add_to_wm(input_link)
            else:
                wme.set_value(new_val)
                wme.update_wm()

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
        vis_objs = set(list(self.w.visible_objects))
        for obj in vis_objs:
            obj_designation = "obj{}".format(obj.object_id)
            if obj_designation in self.objects:
                obj_wme = self.WMEs[obj_designation]
            else:
                self.objects[obj_designation] = obj
                obj_wme = input_link.CreateIdWME("object")
                self.WMEs[obj_designation] = obj_wme
            self.__build_obj_wme_subtree(obj, obj_designation, obj_wme)

        objs_missing = set()
        for obj_dsg in self.objects.keys():
            if self.objects[obj_dsg] not in vis_objs:
                objs_missing.add(obj_dsg)
        for obj_dsg in objs_missing:
            del self.objects[obj_dsg]
            remove_list = [(n, self.WMEs[n]) for n in self.WMEs.keys() if n.startswith(obj_dsg)]
            remove_list = sorted(remove_list, key=lambda s: 1/len(s[0]))
            for wme_name, wme in remove_list:
                del self.WMEs[wme_name]
                if isinstance(wme, psl.SoarWME):
                    wme.remove_from_wm()
                elif isinstance(wme, sml.Identifier):
                    wme.DestroyWME()
                else:
                    raise Exception("WME wasn't of proper type")

        # Finally, we want to check all our on-going actions and handle them appropriately:
        # Actions are by default on the output link and have a `status` attribute already,
        # we just need to update that status if needed
        for action, status_wme, root_id in self.actions:
            if action is None and status_wme is None:
                self.actions.remove((action, status_wme, root_id))
                continue
            if action.is_completed:
                state = "complete" if action.has_succeeded else "failed"
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

        #######
        # SVS #
        #######
        # create and populate lists to add, delete, and change elements in SVS
        navmap = self.w.__dict__['_objects']
        buff = self.svs_buffer
        change_list = []
        add_list = []
        tag_list = [] # used for is_visible tags
        
        # loop through navmap items checking for changes / additions and add to lists to be processed
        for _, val in navmap.items():
            oid = val.object_id
            if not nu.block_init(val):
                if oid in buff:
                    if not nu.blocks_equal(val, buff[oid]):
                        change_list.append(val)
                        if val.is_visible is not buff[oid].is_visible:
                            tag_list.append(f'tag change {oid} is_visible {val.is_visible}')
                        buff[oid] = nu.deepcopy(val)
                else:
                    if val.is_visible:
                        add_list.append(val)
                        tag_list.append(f'tag add {oid} is_visible True')
                        buff[oid] = nu.deepcopy(val)
        
        def send_svs_input(svs_in):
            print('\nSending SVS input: ', svs_in)
            self.agent.agent.SendSVSInput(svs_in)

        for obj in change_list:
            change_input = nu.get_obj_str(obj, 'change')
            send_svs_input(change_input)
        for obj in add_list:
            add_input = nu.get_obj_str(obj, 'add')
            send_svs_input(add_input)
        for tag in tag_list:
            send_svs_input(tag)

    def __build_obj_wme_subtree(self, obj, obj_designation, obj_wme):
        """
        Build a working memory sub-tree for a given perceived object

        :param obj: Cozmo objects.ObservableObject object to put into working memory
        :param obj_designation: Unique string name of the object
        :param obj_wme: sml identifier at the root of the object sub-tree
        :return: None
        """
        obj_input_dict = {
            "object-id": obj.object_id,
            "descriptive-name": obj.descriptive_name,
            "liftable": int(obj.pickupable),
            "pose": {
                "rot": lambda: obj.pose.rotation.angle_z.degrees,
                "x": lambda: obj.pose.position.x,
                "y": lambda: obj.pose.position.y,
                "z": lambda: obj.pose.position.z,
            }
        }
        if isinstance(obj, cozmo.objects.LightCube):
            obj_input_dict["type"] = "led-cube"
            obj_input_dict["connected"] = obj.is_connected
            obj_input_dict["cube-id"] = obj.cube_id
            obj_input_dict["moving"] = obj.is_moving
            obj_input_dict["last-tapped"] = obj.last_tapped_time - self.start_time\
                                            if obj.last_tapped_time is not None else -1.0
            obj_input_dict["name"] = LIGHT_CUBE_NAMES[obj.cube_id]
        elif isinstance(obj, cozmo.objects.Charger):
            #TODO: Handle seeing the charger
            pass
        else:
            cozmo_obj_type = obj.object_type
            temp_arr = cozmo_obj_type.name.split("-")
            obj_type = temp_arr[0]
            
            # fix for names including '-'
            obj_name = ''.join(temp_arr[1:])
            obj_input_dict["type"] = obj_type
            obj_input_dict["name"] = obj_name
        for input_name in obj_input_dict.keys():
            new_val = obj_input_dict[input_name]
            wme = self.WMEs.get(obj_designation + "." + input_name)

            if isinstance(new_val, dict):
                if wme is None:
                    wme = obj_wme.CreateIdWME(input_name)
                    self.WMEs[obj_designation + "." + input_name] = wme
                self.__input_recurse(new_val, obj_designation + "." + input_name, wme)
                continue

            if wme is None:
                wme = psl.SoarWME(input_name, obj_input_dict[input_name])
                wme.add_to_wm(obj_wme)
                self.WMEs[obj_designation + "." + input_name] = wme
            else:
                wme.set_value(obj_input_dict[input_name])
                wme.update_wm()

    def __build_face_wme_subtree(self, face, face_designation, face_wme):
        """
        Build a working memory sub-tree for a given perceived face

        :param face: Cozmo faces.Face object to put into working memory
        :param face_designation: Unique string name of the face
        :param face_wme: sml identifier at the root of the face sub-tree
        :return: None
        """
        face_input_dict = {
            "expression": face.expression,
            "exp-score": face.expression_score,
            "face-id": face.face_id,
            "name": face.name if face.name != "" else "unknown",
            "pose": {
                "rot": lambda: face.pose.rotation.angle_z.degrees,
                "x": lambda: face.pose.position.x,
                "y": lambda: face.pose.position.y,
                "z": lambda: face.pose.position.z,
            }
        }
        for input_name in face_input_dict.keys():
            new_val = face_input_dict[input_name]
            wme = self.WMEs.get(face_designation + "." + input_name)

            if isinstance(new_val, dict):
                if wme is None:
                    wme = face_wme.CreateIdWME(input_name)
                    self.WMEs[face_designation + "." + input_name] = wme
                self.__input_recurse(new_val, face_designation + "." + input_name, wme)
                continue

            if wme is None:
                wme = psl.SoarWME(input_name, face_input_dict[input_name])
                wme.add_to_wm(face_wme)
                self.WMEs[face_designation + "." + input_name] = wme
            else:
                wme.set_value(face_input_dict[input_name])
                wme.update_wm()

    def __input_recurse(self, input_dict, root_name, root_id: sml.Identifier):
        """
        Recursively update WMEs that have a sub-tree structure in the input link.

        We scan through the `input_dict`, which represents the input value getters (or further
        sub-trees) of the sub-tree root, either adding terminal WMEs as usual or further recursing.

        :param input_dict: A dict mapping attributes to getter functions
        :param root_name: The attribute which is the root of this sub-tree
        :param root_id: The sml identifier of the root of the sub-tree
        :return: None
        """
        assert isinstance(input_dict, dict), "Should only recurse on dicts!"

        for input_name in input_dict.keys():
            new_val = input_dict[input_name]
            wme = self.WMEs.get(root_name + "." + input_name)

            if not callable(new_val):
                if wme is None:
                    wme = root_id.CreateIdWME(input_name)
                    self.WMEs[root_name + "." + input_name] = wme
                self.__input_recurse(new_val, root_name + "." + input_name, wme)
                continue

            new_val = new_val()
            if wme is None:
                new_wme = psl.SoarWME(att=input_name, val=new_val)
                self.WMEs[root_name + "." + input_name] = new_wme
                new_wme.add_to_wm(root_id)
            else:
                wme.set_value(new_val)
                wme.update_wm()


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


def define_custom_objects_from_file(world: cozmo.world.World, filename: str):
    # define a unique cube (44mm x 44mm x 44mm) (approximately the same size as a light cube)
    # with a 30mm x 30mm Diamonds2 image on every face
    # cube_obj = world.define_custom_cube(CustomObjectTypes.CustomType00,
    #                                           CustomObjectMarkers.Diamonds2,
    #                                           44,
    #                                           30, 30, True)

    # define a unique cube (88mm x 88mm x 88mm) (approximately 2x the size of a light cube)
    # with a 50mm x 50mm Diamonds3 image on every face
    # big_cube_obj = world.define_custom_cube(CustomObjectTypes.CustomType01,
    #                                           CustomObjectMarkers.Diamonds3,
    #                                           88,
    #                                           50, 50, True)


    # define a unique box (60mm deep x 140mm width x100mm tall)
    # with a different 30mm x 50mm image on each of the 6 faces
    # box_obj = world.define_custom_box(cust_type('box', 'box'),
    #                                         CustomObjectMarkers.Hexagons2,  # front
    #                                         CustomObjectMarkers.Circles3,   # back
    #                                         CustomObjectMarkers.Circles4,   # top
    #                                         CustomObjectMarkers.Circles5,   # bottom
    #                                         CustomObjectMarkers.Triangles4, # left
    #                                         CustomObjectMarkers.Triangles3, # right
    #                                         60, 140, 100,
    #                                         30, 50, True)
    obj_tree = ET.parse(filename)
    obj_root = obj_tree.getroot()
    custom_objects = []
    
    # find attribute.text from node n
    def f(n, attr):
        return n.find(attr).text
    
    for obj_node in obj_root:
        obj_type = obj_node.tag
        obj_unique = True if obj_node.attrib['unique'] == "true" else False
        obj_name = f(obj_node, 'name')
        obj_marker = f(obj_node, 'marker')
        obj_marker_node = obj_node.find('marker')
        obj_marker_height = int(obj_marker_node.attrib['height'])
        obj_marker_width = int(obj_marker_node.attrib['width'])
        cozmo_object_type = custom_object_type_factory(obj_type, obj_name)
        
        if obj_type == "cube":
            obj_size = int(f(obj_node, 'size'))
            custom_object = world.define_custom_cube(
                custom_object_type=cozmo_object_type,
                marker=MARKER_DICT[obj_marker],
                size_mm=obj_size,
                marker_width_mm=obj_marker_width,
                marker_height_mm=obj_marker_height,
                is_unique=obj_unique)
            custom_objects.append(custom_object)
        
        # wall or box
        else:
            obj_width = int(f(obj_node, 'width'))
            obj_height = int(f(obj_node, 'height'))

            if obj_type == "wall":
                custom_object = world.define_custom_wall(
                    custom_object_type=cozmo_object_type,
                    marker=MARKER_DICT[obj_marker],
                    width_mm=obj_width,
                    height_mm=obj_height,
                    marker_width_mm=obj_marker_width,
                    marker_height_mm=obj_marker_height,
                    is_unique=obj_unique)
                custom_object.name = obj_name
                custom_objects.append(custom_object)
            
            if obj_type == "box":
                obj_depth = int(f(obj_node, 'depth'))
                mh = lambda node, loc: MARKER_DICT[f(node, f'marker-{loc}')]
                custom_object = world.define_custom_box(cozmo_object_type,
                    mh(obj_node, 'front'),
                    mh(obj_node, 'back'),
                    mh(obj_node, 'top'),
                    mh(obj_node, 'bottom'),
                    mh(obj_node, 'left'),
                    mh(obj_node, 'right'),
                    obj_depth, obj_width, obj_height,
                    obj_marker_height, obj_marker_width, obj_unique)
                custom_object.name = obj_name
                custom_objects.append(custom_object)
    return custom_objects
