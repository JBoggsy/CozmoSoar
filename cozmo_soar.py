from collections import namedtuple

import soar.Python_sml_ClientInterface as sml
import cozmo
from cozmo.robot import Robot
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

    def update_input(self):
        """
        Update the Soar input link WMEs.

        We take advantage of the fact that WorkingMemoryElement objects can update Soar
        recursively here by just calling the ``update`` method of the input-link WME.
        """
        self.in_link.update()

    def load_productions(self, filename):
        self.a.LoadProductions(filename)


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

    def create_child_wme(self, name, attr_dict=None):
        """
        Create a new WorkingMemoryElement as a child to this one.

        This function creates a new WME in Soar and then a new WME object in python using the
        passed in attribute dict, then ties the new python WME to this one as an attribute.

        :param name: Name of the new WME. Must be unique within this WME's attributes
        :param attr_dict: A dict of name-value pairs for initial attributes to the WME
        :return: The new python WME object
        """
        new_soar_wme = self.agent.CreateIdWME(self.wme_ref, name)
        new_py_wme = WorkingMemoryElement(name, new_soar_wme, self.agent, attr_dict)

        self.__attr_vals[name] = new_py_wme
        self.attr_refs[name] = new_soar_wme

        self.agent.Commit()
        return new_py_wme

    def update(self):
        attr_vals = self.attr_vals  # Should save time due to nature of self.attr_vals
        for name in self.attr_refs:
            if isinstance(attr_vals[name], WorkingMemoryElement):
                attr_vals[name].update()
            else:
                self.agent.Update(self.attr_refs[name], attr_vals[name])
        self.agent.Commit()
