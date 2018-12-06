from collections import namedtuple

import soar.Python_sml_ClientInterface as sml
import cozmo
from cozmo.faces import EvtFaceAppeared, EvtFaceObserved, EvtFaceIdChanged, EvtFaceDisappeared
from cozmo.robot import Robot
from cozmo.objects import LightCube, LightCubeIDs
from cozmo.camera import Camera
from cozmo.util import degrees, distance_mm, speed_mmps


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
        self.light_cubes = [self.w.get_light_cube(i) for i in LightCubeIDs]

        self.kernel = self.k = kernel
        self.agent = self.a = self.kernel.CreateAgent(name)
        self.in_link_ref = self.a.GetInputLink()
        self.in_link = WorkingMemoryElement("input-link", self.in_link_ref, self.agent)

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
                              lambda: self.w.visible_face_count())
        self.in_link.add_attr('obj_count',
                              lambda: self.w.visible_object_count())
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

        # Initialize light cube WMEs
        for l_cube in self.light_cubes:
            if l_cube is None:
                continue
            self.init_light_cube_wme(l_cube)

        # Initialize face WMEs
        for f in self.w.visible_faces:
            self.init_face_wme(f)

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

    def handle_command(self, command: sml.Identifier, agent: sml.Agent):
        """
        Handle a command produced by Soar.

        This basically just maps command names to their cozmo methods.

        :param command: A Soar command object
        :return: True if successful, False otherwise
        """
        comm_name = command.GetCommandName()

        if comm_name == "move-lift":
            return self.__handle_move_lift(command, agent)

        print("Error: Don't know how to handle command {}".format(comm_name))
        return False

    def __handle_move_lift(self, command, agent):
        """
        Handle a Soar move-life action.

        The Soar output should look like:
        (I3 ^move-lift Vx)
          (Vx ^height [height])
        where [hieght] is a real number in the range [0, 1]. This command moves the lift to the
        the given height, where 0 is the lowest possible position and 1 is the highest.

        :param command: Soar command object
        :param agent: Soar Agent object
        :return: True if successful, False otherwise
        """
        height = float(command.GetParameterValue("height"))
        print("Moving lift {}".format(height))
        set_lift_height_action = self.robot.set_lift_height(height)
        set_lift_height_action.wait_for_completed()
        command.AddStatusComplete()
        agent.Commit()

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

    def __handle_face_disappear(self, evt, face):
        """
        Callback for when a face leaves Cozmo's vision; removes face from input link.

        :param evt: Event object
        :param face: Face object which left view
        :return: None
        """
        self.in_link.rem_attr("face-{}".format(face.face_id))


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
            raise KeyError("Cannot have duplicate attribute names")
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
