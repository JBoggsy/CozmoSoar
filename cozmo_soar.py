from collections import namedtuple

import soar.Python_sml_ClientInterface as sml
import cozmo
from cozmo.action import EvtActionCompleted
from cozmo.faces import EvtFaceAppeared, EvtFaceDisappeared
from cozmo.lights import Light, Color
from cozmo.robot import Robot
from cozmo.objects import LightCube, LightCubeIDs, EvtObjectAppeared, EvtObjectDisappeared
from cozmo.camera import Camera
from cozmo.util import degrees, distance_mm, speed_mmps

COLORS = ['red', 'blue', 'green', 'white', 'off']


class CozmoSoar(object):
    """
    A class representing the Soar interface with a Cozmo robot.

    A `CozmoSoar` object holds a reference to two critical things: a `cozmo.Robot` instance used
    to talk with the actual Cozmo robot, and a `sml.Agent` instance used to communicate with the
    Soar kernel. A `CozmoSoar` instance is then used by the debugger itself to easily get
    information to and from both the Soar agent and the actual Cozmo robot.
    """


    def __init__(self, robot: Robot, kernel: sml.Kernel, name: str):
        """
        Create a new `CozmoState` instance with the given robot and agent.

        :param robot: The Cozmo robot to interface with
        :param agent: The SML agent in Soar to communicate with
        """
        self.name = name

        self.robot = self.r = robot
        self.world = self.w = self.r.world
        self.world.add_event_handler(EvtFaceAppeared, self.__handle_face_appear)
        self.world.add_event_handler(EvtFaceDisappeared, self.__handle_face_disappear)
        self.world.add_event_handler(EvtObjectAppeared, self.__handle_obj_appear)
        self.world.add_event_handler(EvtObjectDisappeared, self.__handle_obj_disappear)

        self.objects = {}
        self.faces = {}

        self.kernel = self.k = kernel
        self.agent = self.a = self.kernel.CreateAgent(name)
        self.in_link_ref = self.a.GetInputLink()
        self.in_link = WorkingMemoryElement("input-link", self.in_link_ref, self.agent)
        self.action_failure = None

        self.init_in_link()

    def init_in_link(self):
        """
        Initialize the Soar input link.

        Create Working Memory Elements (WMEs) for each piece of input data the
        Soar agents gets, initialized to the current value.

        :return: None
        """
        # First, we'll initialize simple WMEs which don't need an IdWME
        self.in_link.add_attr('battery_voltage',
                              lambda: self.r.battery_voltage)
        self.in_link.add_attr('carrying_block',
                              lambda: int(self.r.is_carrying_block))
        self.in_link.add_attr('carrying_object_id',
                              lambda: self.r.carrying_object_id)
        self.in_link.add_attr('charging',
                              lambda: int(self.r.is_charging))
        self.in_link.add_attr('cliff_detected',
                              lambda: int(self.r.is_cliff_detected))
        self.in_link.add_attr('head_angle',
                              lambda: self.r.head_angle.radians)
        self.in_link.add_attr('face_count',
                              self.w.visible_face_count)
        self.in_link.add_attr('obj_count',
                              lambda: len(self.objects))
        self.in_link.add_attr('picked_up',
                              lambda: int(self.r.is_picked_up))
        self.in_link.add_attr('robot_id',
                              lambda: self.r.robot_id)
        self.in_link.add_attr('serial',
                              self.r.serial)

        # Now we initialize more complex WMEs which need special IdWMEs
        lift_attr_dict = {'angle': lambda: self.r.lift_angle.radians,
                          'height': lambda: self.r.lift_height.distance_mm,
                          'ratio': lambda: self.r.lift_ratio}
        lift_wme = self.in_link.create_child_wme('lift', lift_attr_dict)

        pose_attr_dict = {'rot': lambda: self.r.pose.rotation.angle_z.radians,
                          'x': lambda: self.r.pose.position.x,
                          'y': lambda: self.r.pose.position.y,
                          'z': lambda: self.r.pose.position.z}
        pose_wme = self.in_link.create_child_wme('pose', pose_attr_dict)

        # Initialize object WMEs (right now only light cubes)
        for o in self.w.visible_objects:
            if isinstance(o, cozmo.objects.LightCube):
                self.init_light_cube_wme(o)
            self.objects[o.object_id] = o

        # Initialize face WMEs
        for f in self.w.visible_faces:
            self.init_face_wme(f)
            self.faces[f.face_id] = f

    def init_light_cube_wme(self, l_cube):
        l_cube_attr_dict = {'object_id': l_cube.object_id,
                            'connected': lambda: l_cube.is_connected,
                            'cube_id': lambda: l_cube.cube_id,
                            'descriptive_name': lambda: l_cube.descriptive_name,
                            'moving': lambda: int(l_cube.is_moving),
                            'liftable': lambda: int(l_cube.pickupable),
                            'type': "cube",
                            'visible': lambda: int(l_cube.is_visible)}
        l_cube_wme = self.in_link.create_child_wme(l_cube.descriptive_name,
                                                   l_cube_attr_dict,
                                                   soar_name='object')

        # Add pose WME for cube
        lc_pose_attr_dict = {'rot': lambda: l_cube.pose.rotation.angle_z.radians,
                             'x': lambda: l_cube.pose.position.x,
                             'y': lambda: l_cube.pose.position.y,
                             'z': lambda: l_cube.pose.position.z}
        lc_pose_wme = l_cube_wme.create_child_wme('pose', lc_pose_attr_dict)

    def init_face_wme(self, face):
        new_face_wme_attr_dict = {
            'name': lambda: face.name,
            'face_id': lambda: face.face_id,
            'expression': lambda: face.expression,
            'expression_conf': lambda: face.expression_score
        }
        face_wme = self.in_link.create_child_wme("face-{}".format(face.face_id),
                                                new_face_wme_attr_dict,
                                                soar_name='face')

        # Add pose WME for face
        face_pose_attr_dict = {'rot': lambda: face.pose.rotation.angle_z.radians,
                               'x': lambda: face.pose.position.x,
                               'y': lambda: face.pose.position.y,
                               'z': lambda: face.pose.position.z}
        lc_pose_wme = face_wme.create_child_wme('pose', face_pose_attr_dict)

    def update_input(self):
        """
        Update the Soar input link WMEs.

        We take advantage of the fact that WorkingMemoryElement objects can update Soar
        recursively here by just calling the ``update`` method of the input-link WME.
        """
        self.in_link.update()

    def load_productions(self, filename):
        """
        Load Soar productions for the Agent to use.

        :param filename: Soar production file to load
        :return: None
        """
        self.a.LoadProductions(filename)

    ####################
    # COMMAND HANDLING #
    ####################

    def handle_command(self, command: sml.Identifier, agent: sml.Agent):
        """
        Handle a command produced by Soar.

        This basically just maps command names to their cozmo methods.

        :param command: A Soar command object
        :return: True if successful, False otherwise
        """
        comm_name = command.GetCommandName().lower()

        if comm_name == "move-lift":
            success = self.__handle_move_lift(command, agent)
        elif comm_name == "go-to-object":
            success = self.__handle_go_to_object(command, agent)
        elif comm_name == "turn-to-face":
            success = self.__handle_turn_to_face(command, agent)
        elif comm_name == "set-backpack-lights":
            success = self.__handle_set_backpack_lights(command, agent)
        elif comm_name == "drive-forward":
            success = self.__handle_drive_forward(command, agent)
        elif comm_name == "turn-in-place":
            success = self.__handle_turn_in_place(command, agent)
        else:
            raise NotImplementedError("Error: Don't know how to handle command {}".format(comm_name))

        if not success:
            command.AddStatusComplete()

        return True

    def __handle_turn_to_face(self, command, agent):
        """
        Handle a Soar turn-to-face action.

        The Soar output should look like:
        (I3 ^turn-to-face Vx)
          (Vx ^face-id [fid])
        where [fid] is the integer ID associated with the face to turn towards.

        :param command: Soar command object
        :param agent: Soar Agent object
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
        turn_towards_face_action = self.r.turn_towards_face(target_face)
        callback = self.__handle_action_complete_factory(command)
        turn_towards_face_action.add_event_handler(EvtActionCompleted, callback)
        return True

    def __handle_move_lift(self, command, agent):
        """
        Handle a Soar move-lift action.

        The Soar output should look like:
        (I3 ^move-lift Vx)
          (Vx ^height [hgt])
        where [hgt] is a real number in the range [0, 1]. This command moves the lift to the
        the given height, where 0 is the lowest possible position and 1 is the highest.

        :param command: Soar command object
        :param agent: Soar Agent object
        :return: True if successful, False otherwise
        """
        try:
            height = float(command.GetParameterValue("height"))
        except ValueError as e:
            print("Invalid height format {}".format(command.GetParameterValue("height")))
            return False

        print("Moving lift {}".format(height))
        set_lift_height_action = self.robot.set_lift_height(height)
        callback = self.__handle_action_complete_factory(command)
        set_lift_height_action.add_event_handler(EvtActionCompleted, callback)
        return True

    def __handle_go_to_object(self, command, agent):
        """
        Handle a Soar go-to-object action.

        The Sour output should look like:
        (I3 ^go-to-object Vx)
          (Vx ^target_object_id [id])
        where [id] is the object id of the object to go to. Cozmo will stop 150mm from the object.

        :param command: Soar command object
        :param agent: Soar Agent object
        :return: True if successful, False otherwise
        """
        try:
            target_id = int(command.GetParameterValue("target_object_id"))
        except ValueError as e:
            print("Invalid target-object-id format {}".format(command.GetParameterValue("target_object_id")))
        if target_id not in self.objects.keys():
            print("Couldn't find target object")
            return False

        print("Going to object {}".format(target_id))
        target_obj = self.objects[target_id]
        go_to_object_action = self.robot.go_to_object(target_obj, distance_mm(150))
        callback = self.__handle_action_complete_factory(command)
        go_to_object_action.add_event_handler(EvtActionCompleted, callback)
        return True

    def __handle_set_backpack_lights(self, command, agent):
        """
        Handle a Soar set-backpack-lights action.

        The Sour output should look like:
        (I3 ^set-backpack-lights Vx)
          (Vx ^color [color])
        where [color] is a string indicating which color the lights should be set to. The colors
        are "red", "blue", "green", "white", and "off".

        :param command: Soar command object
        :param agent: Soar Agent object
        :return: True if successful, False otherwise
        """
        color_str = command.GetParameterValue("color")
        if color_str not in COLORS:
            print("Invalid backpack lights color {}".format(color_str))
            return False
        elif color_str == 'red':
            light = cozmo.lights.red_light
        elif color_str == 'green':
            light = cozmo.lights.green_light
        elif color_str == 'blue':
            light = cozmo.lights.blue_light
        elif color_str == 'white':
            light = cozmo.lights.white_light
        else:
            light = cozmo.lights.off_light

        self.r.set_all_backpack_lights(light=light)
        command.AddStatusComplete()
        return True

    def __handle_drive_forward(self, command, agent):
        """
        Handle a Soar drive-forward action.

        The Sour output should look like:
        (I3 ^drive-forward Vx)
          (Vx ^distance [dist]
              ^speed [spd])
        where [dist] is a real number indicating how far Cozmo should travel (negatives go
        backwards) and speed is how fast Cozmo should travel. Units are mm and mm/s, respectively.

        :param command: Soar command object
        :param agent: Soar Agent object
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
        drive_forward_action = self.r.drive_straight(distance, speed)
        callback = self.__handle_action_complete_factory(command)
        drive_forward_action.add_event_handler(EvtActionCompleted, callback)
        return True

    def __handle_turn_in_place(self, command, agent):
        """
        Handle a Soar turn-in-place action.

        The Sour output should look like:
        (I3 ^turn-in-place Vx)
          (Vx ^angle [ang]
              ^speed [spd])
        where [ang] is the amount Cozmo should rotate in degrees and speed is the speed at which
        Cozmo should rotate in deg/s.

        :param command: Soar command object
        :param agent: Soar Agent object
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

        print("Rotating in place {} radians at {}rad/s".format(angle.degrees, speed.degrees))
        turn_in_place_action = self.r.turn_in_place(angle=angle, speed=speed)
        callback = self.__handle_action_complete_factory(command)
        turn_in_place_action.add_event_handler(EvtActionCompleted, callback)
        return True

    def __handle_action_complete_factory(self, command):
        def __handle_action_complete(evt, action, failure_code, failure_reason, state):
            if state == cozmo.action.ACTION_SUCCEEDED:
                print("Action {} finished successfully".format(action))
            else:
                print("Action {} terminated because {}".format(action, failure_reason))
            command.AddStatusComplete()
        return __handle_action_complete

    #########################
    # OBJECT/FACE DETECTION #
    #########################

    def __handle_obj_appear(self, evt, updated, obj, image_box, pose):
        if isinstance(obj, cozmo.objects.LightCube):
            self.init_light_cube_wme(obj)
        self.objects[obj.object_id] = obj
        print("Saw new object {}".format(obj.object_id))

    def __handle_obj_disappear(self, evt, obj):
        self.in_link.rem_attr(obj.descriptive_name)
        del self.objects[obj.object_id]
        print("Lost sight of object {}".format(obj.object_id))

    def __handle_face_appear(self, evt, face, image_box, name, pose, updated):
        """
        Callback method for when Cozmo sees a new face; adds face to input link.

        Cozmo SDK guarantees that this will be called only the very first time a certain face is
        seen, unless the face has disappeared in the interim. As such, we know that this will be
        called only once before ``__handle_face_disappear`` is called, and so making a new WME is
        fine.

        :param evt: Event object
        :param face: New ``Cozmo.faces.Face`` object for newly detected face
        :param image_box: Image box around the face
        :param name: Name assigned to the face
        :param pose: Estimated pose of the face (as a Cozmo ``Pose`` object)
        :param updated: List of attributes updated
        :return: None
        """
        new_face_wme_attr_dict = {
            'name': lambda: face.name,
            'face_id': lambda: face.face_id,
            'expression': lambda: face.expression,
            'expression_conf': lambda: face.expression_score
        }
        face_wme = self.in_link.create_child_wme("face-{}".format(face.face_id),
                                                new_face_wme_attr_dict,
                                                soar_name='face')

        # Add pose WME for face
        face_pose_attr_dict = {'rot': lambda: face.pose.rotation.angle_z.radians,
                               'x': lambda: face.pose.position.x,
                               'y': lambda: face.pose.position.y,
                               'z': lambda: face.pose.position.z}
        lc_pose_wme = face_wme.create_child_wme('pose', face_pose_attr_dict)
        self.faces[face.face_id] = face
        print("Added face {}".format(face.face_id))

    def __handle_face_disappear(self, evt, face):
        """
        Callback for when a face leaves Cozmo's vision; removes face from input link.

        :param evt: Event object
        :param face: Face object which left view
        :return: None
        """
        self.in_link.rem_attr("face-{}".format(face.face_id))
        del self.faces[face.face_id]
        print("Removed face {}".format(face.face_id))


class WorkingMemoryElement(object):
    """
    Represents a Soar Working Memory Element (WME) in python.

    This is a convenience class to help keep track of WMEs. Each WME should have three things:
    a reference to a Python representation of a WME in a Soar agent, a reference to a Soar agent,
    and a dict of attribute-value pairs. The Soar WME and agent are used to update that particular
    WME in Soar, and the values of the attributes can be either static or a function which
    returns a value. Technically, two dicts are maintained: one keeps track of attribute values
    and the other keeps track of the SML references to the attributes in Soar.

    The class also has various helper functions. ``WorkingMemoryElemnt.update()`` method
    updates the WME in Soar appropriately, including recursively calling ``update`` on any
    WorkingMemoryElement-valued attributes. New non-WME attributes can be added to a
    WorkingMemoryElement on the fly by calling the ``WorkingMemoryElement.add_attr`` method,
    and similarly attributes can be removed with the ``WorkingMemoryElement.rem_attr`` method. A
    WME can have another WME as the value of an attribute, allowing the creation of a WME graph,
    essentially duplicating  the one in Soar. However, to add a WME-valued attribute to an
    existing WME you must call ``WorkingMemoryElement.create_child_wme`` rather than
    ``WorkingMemoryElement.add_attr``.

    Note that right now, a WME represented with this object requires each
    attribute to have a unique name, unlike Soar.
    """
    def __init__(self, name: str, wme_ref, agent: sml.Agent, attr_dict=None):
        """
        Create a new WorkingMemoryElement with the given parameters.

        The new WME has the given name, and represents the passed in Soar WME reference of the
        given Soar agent. If the ``attr_dict`` parameter is not none, then when the new WME is
        initialized, it goes through the dict and creates new Soar WMEs based on the key-value
        pairs, such that each new WME is a attribute of the WME the object represents which has
        the dictionary key and value as its name and value, respectively. For example,
        if the WME the new object represents is the input-link of an agent, the dict

            {'speed': 500,
             'angle': 27.8,
             'flight': 'AA999`}

        would create three new attributes of the input-link, speed, angle, and flight, with the
        given values.

        The values in the attribute dictionary can be callable. If they are, the output should
        be either an int, a float, or a string. If the result is not one of those, it will be
        coerced into a string.

        :param name: The name of the WME represented by the object
        :param wme_ref: Python object representing the WME in Soar
        :param agent: Python object representing the agent in Soar whose WME this is
        :param attr_dict: A dict of name-value pairs for initial attributes to the WME
        """
        self.name = name
        self.wme_ref = wme_ref
        self.agent = agent
        self.__attr_vals = dict()
        self.attr_refs = dict()
        if attr_dict is not None:
            for attr_name in attr_dict:
                self.add_attr(attr_name, attr_dict[attr_name])

    @property
    def attr_vals(self):
        """
        Returns the attribute name-value dictionary.

        This function exists because the object allows attribute values to be callable or
        non-callable (e.g., int/float/string or function). Intuitively, when we call
        wme.attributes[attr_name], we want it to return the value of the given attribute,
        not a function. Thus, the actual dict of attributes is hidden as WME.__attributes and
        this property function just scans that and calls functions as needed to produce a dict
        which only has values. The @property decorator means this function is called without
        parentheses: ``wme.attributes`` rather than ``wme.attributes()``, so that getting an
        individual attribute still looks like ``wme.attribute[attr_name]``.

        Note: Theoretically we don't need to scan self.__attributes at all, and not doing so
        would be more efficient.

        :return: A dict hold attribute-value pairs.
        """
        attr_dict = dict()
        for name in self.__attr_vals:
            attr = self.__attr_vals[name]
            attr_dict[name] = attr() if callable(attr) else attr
        return attr_dict

    def add_attr(self, name, value_or_getter):
        """
        Add a new attribute to the WME with the given name.

        The `` value_or_getter`` parameter can be either a static value or a function which
        returns a single value. If it is callable and the value returned is not an int, float,
        or string, the value will be coerced into a string.

        :param name: The name of the attribute
        :param value_or_getter: Value or function which returns a value
        """
        if name in self.__attr_vals.keys():
            raise KeyError("Cannot have duplicate attribute names: {}".format(name))
        if not callable(value_or_getter):
            self.__attr_vals[name] = value_or_getter
            self.attr_refs[name] = self.__create_simple_wme_ref(name, value_or_getter)
            return

        # The function below wraps the given getter function and checks the output type. If the
        # output type isn't one of the valid ones, it coerces it into a string.
        def type_check_wrapper(getter):
            def type_check():
                val = getter()
                if type(val) not in [int, float, str]:
                    return str(val)
                else:
                    return val
            return type_check
        current_value = type_check_wrapper(value_or_getter)()
        self.__attr_vals[name] = type_check_wrapper(value_or_getter)
        self.attr_refs[name] = self.__create_simple_wme_ref(name, current_value)

    def rem_attr(self, name):
        """
        Remove the attribute with the given name from Soar and the WME.

        :param name: Name of attribute to remove
        """
        if not self.has_attr(name):
            # TODO Log here
            raise KeyError("WME {} has no attribute {}".format(self.name, name))
        self.agent.DestroyWME(self.attr_refs[name])
        del self.attr_refs[name]
        del self.__attr_vals[name]

    def has_attr(self, name):
        return name in self.__attr_vals.keys()

    def __create_simple_wme_ref(self, name, val):
        """
        Given a name and a value, create a type-appropriate WME in Soar and return reference.

        :param name: Name of the new WME
        :param val: Value of the new WME
        :return: A reference to the WME
        """
        if type(val) == int:
            new_wme = self.agent.CreateIntWME(self.wme_ref,
                                              name,
                                              val)
        elif type(val) == float:
            new_wme = self.agent.CreateFloatWME(self.wme_ref,
                                                name,
                                                val)
        elif type(val) == str:
            new_wme = self.agent.CreateStringWME(self.wme_ref,
                                                 name,
                                                 val)
        else:
            # TODO: Put a logging warning here
            new_wme = self.agent.CreateStringWME(self.wme_ref,
                                                 name,
                                                 str(val))
        self.agent.Commit()
        return new_wme

    def create_child_wme(self, name, attr_dict=None, soar_name=None):
        """
        Create a new WorkingMemoryElement as a child to this one.

        This function creates a new WME in Soar and then a new WME object in python using the
        passed in attribute dict, then ties the new python WME to this one as an attribute.

        :param name: Name of the new WME. Must be unique within this WME's attributes
        :param attr_dict: A dict of name-value pairs for initial attributes to the WME
        :param soar_name: Name for attribute connection in Soar, can be a duplicate
        :return: The new python WME object
        """
        if soar_name is None:
            soar_name = name
        new_soar_wme = self.agent.CreateIdWME(self.wme_ref, soar_name)
        new_py_wme = WorkingMemoryElement(name, new_soar_wme, self.agent, attr_dict)

        self.__attr_vals[name] = new_py_wme
        self.attr_refs[name] = new_soar_wme

        self.agent.Commit()
        return new_py_wme

    def update(self):
        """
        Recursively update the WMEs in Soar based on the attribute values.

        :return: None
        """
        attr_vals = self.attr_vals  # Should save time due to nature of self.attr_vals
        for name in self.attr_refs:
            if isinstance(attr_vals[name], WorkingMemoryElement):
                attr_vals[name].update()
            else:
                self.agent.Update(self.attr_refs[name], attr_vals[name])
        self.agent.Commit()

    def __str__(self):
        """
        Print the WME by showing attribute names and values.

        :return: String representation of the WME
        """
        ret_str = "<WME>{}:\n".format(self.name)
        for name in self.attr_refs:
            ret_str += "|--{}:{}\n".format(name, self.attr_vals[name])
        return ret_str
