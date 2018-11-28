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

    Note to Nick:
        There are some weird syntax things here that I ought to explain.
        1. Some parameters look like "name: class". The class after the : doesn't do anything
        directly, it just tells the IDE what kind of object the parameter will be, which lets it
        autocomplete for us.
        2. The "@property" thing above some functions is called an annotation, and tells the
        interpreter the function is special. @property tells it to treat the method as a
        property, so that the method can be called like "self.[method_name]" instead of
        "self.[method_name]()". E.g., "self.battery_voltage" rather than "self.battery_voltage()"
        3. A lot of the methods are currently stubs or placeholders. Anything not actually
        finished shouldn't return anything, but raise "NotImplementedError" instead.
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
        self.in_link = self.a.GetInputLink()

        self.wmes = dict()
        self.init_in_link()

    def init_in_link(self):
        """
        Initialize the Soar input link.

        Create Working Memory Elements (WMEs) for each piece of input data the
        Soar agents gets, initialized to the current value.

        :return: None
        """
        # First, we'll initialize simple WMEs which don't need an IdWME
        self.wmes['battery_voltage'] = self.a.CreateFloatWME(self.in_link,
                                                             'battery_voltage',
                                                             self.r.battery_voltage)
        self.wmes['carrying_block'] = self.a.CreateIntWME(self.in_link,
                                                          'carrying_block',
                                                          int(self.r.is_carrying_block))
        self.wmes['charging'] = self.a.CreateIntWME(self.in_link,
                                                    'charging',
                                                    int(self.r.is_charging))
        self.wmes['cliff_detected'] = self.a.CreateIntWME(self.in_link,
                                                          'cliff_detected',
                                                          int(self.r.is_cliff_detected))
        self.wmes['head_angle'] = self.a.CreateFloatWME(self.in_link,
                                                        'head_angle',
                                                        self.r.head_angle.radians)
        self.wmes['face_count'] = self.a.CreateIntWME(self.in_link,
                                                      'face_count',
                                                      self.w.visible_face_count())
        self.wmes['obj_count'] = self.a.CreateIntWME(self.in_link,
                                                     'obj_count',
                                                     self.w.visible_object_count())
        self.wmes['picked_up'] = self.a.CreateIntWME(self.in_link,
                                                     'picked_up',
                                                     self.r.is_picked_up)
        self.wmes['robot_id'] = self.a.CreateIntWME(self.in_link,
                                                    'robot_id',
                                                    self.r.robot_id)
        self.wmes['serial'] = self.a.CreateStringWME(self.in_link,
                                                     'serial',
                                                     self.r.serial)

        # Now we initialize more complex WMEs which need special IdWMEs
        # TODO: Fill this in

        # Now commit changes to Soar Kernel
        self.agent.Commit()

    def update_input(self):
        """
        Update the Soar input link WMEs.

        Because multiple WMEs in Soar can have the same attribute name, we need to update the
        specific WMEs we created in ``init_in_link``, rather than just being able to update
        the value of the ``self.wmes`` dictionary.

        :return: None
        """
        # First, we'll update simple WMEs which don't need an IdWME
        self.agent.Update(self.wmes['battery_voltage'],
                          self.r.battery_voltage)

        self.agent.Update(self.wmes['carrying_block'],
                          int(self.r.is_carrying_block))

        self.agent.Update(self.wmes['charging'],
                          int(self.r.is_charging))

        self.agent.Update(self.wmes['cliff_detected'],
                          int(self.r.is_cliff_detected))

        self.agent.Update(self.wmes['head_angle'],
                          self.r.head_angle.radians)

        self.agent.Update(self.wmes['face_count'],
                          self.w.visible_face_count())

        self.agent.Update(self.wmes['obj_count'],
                          self.w.visible_object_count())

        self.agent.Update(self.wmes['picked_up'],
                          self.r.is_picked_up)

        self.agent.Update(self.wmes['robot_id'],
                          self.r.robot_id)

        self.agent.Update(self.wmes['serial'],
                          self.r.serial)

        # Now we initialize more complex WMEs which need special IdWMEs
        # TODO: Fill this in

        # Now commit changes to Soar Kernel
        self.agent.Commit()

    def load_productions(self, filename):
        self.a.LoadProductions(filename)
