import PySoarLib as psl
import soar.Python_sml_ClientInterface as sml

import cozmo

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

        self.cam = self.r.camera
        self.cam.image_stream_enabled = True
        self.r.enable_facial_expression_estimation()

        self.objects = {}
        self.faces = {}

        #######################
        # Working Memory data #
        #######################

        # self.static_inputs maps each static input to a function to retrieve its latest value from
        #   Soar. A static input is one that won't ever disappear, in contrast to temporary inputs
        #   like faces or objects
        self.static_inputs = {'battery_voltage': lambda: self.r.battery_voltage,
                              'carrying_block': lambda: int(self.r.is_carrying_block),
                              'carrying_object_id': lambda: self.r.carrying_object_id,
                              'charging': lambda: int(self.r.is_charging),
                              'cliff_detected': lambda: int(self.r.is_cliff_detected),
                              'head_angle': lambda: self.r.head_angle.radians,
                              'face_count': self.w.visible_face_count,
                              'object_count': lambda : len(self.objects),
                              'picked_up': lambda: int(self.r.is_picked_up),
                              'robot_id': lambda: self.r.robot_id,
                              'serial': lambda: self.r.serial,
                              'pose': {'rot': lambda: self.r.pose.rotation.angle_z.radians,
                                       'x': lambda: self.r.pose.position.x,
                                       'y': lambda: self.r.pose.position.y,
                                       'z': lambda: self.r.pose.position.z},
                              'lift': {'angle': lambda: self.r.lift_angle.radians,
                                       'height': lambda: self.r.lift_height.distance_mm,
                                       'ratio': lambda: self.r.lift_ratio}
                              }

        # self.WMEs maps SoarWME objects to their attribute names for easier retrieval. Since Cozmo
        #   inputs will always be one-to-one with their values (i.e., there won't be multiple values
        #   with the same name), a standard dictionary is fine
        self.WMEs = {}

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
                new_wme = psl.SoarWME(att=input_name,
                                      val=new_val)
                self.WMEs[input_name] = new_wme
                new_wme.add_to_wm(input_link)
            else:
                wme.set_value(new_val)
                wme.update_wm()

        # Then, check through the visible faces and objects to see if they need to be added,
        # updated, or removed
        for face in self.w.visible_faces:
            face_designation = "face{}".format(face.face_id)
            if face_designation in self.faces:
                self.faces[face_designation] = True
                face_wme = self.WMEs[face_designation]
            else:
                self.faces[face_designation] = True
                face_wme = input_link.CreateIdWME("face")
                self.WMEs[face_designation] = face_wme
            self.__build_face_wme_subtree(face, face_designation, face_wme)

        for obj in self.w.visible_objects:
            obj_designation = "obj{}".format(obj.object_id)
            if obj_designation in self.objects:
                self.objects[obj_designation] = True
                obj_wme = self.WMEs[obj_designation]
            else:
                self.objects[obj_designation] = True
                obj_wme = input_link.CreateIdWME("object")
                self.WMEs[obj_designation] = obj_wme
            self.__build_obj_wme_subtree(obj, obj_designation, obj_wme)

    def __build_obj_wme_subtree(self, obj, obj_designation, obj_wme):
        """
        Build a working memory sub-tree for a given perceived object

        :param obj: Cozmo objects.ObservableObject object to put into working memory
        :param obj_designation: Unique string name of the object
        :param obj_wme: sml identifier at the root of the object sub-tree
        :return: None
        """
        obj_input_dict = {'object_id': obj.object_id,
                         'descriptive_name': obj.descriptive_name,
                         'distance': obj_distance_factory(self.r, obj)(),
                         'heading': obj_heading_factory(self.r, obj)(),
                         'liftable': int(obj.pickupable),
                         'type': "object"}
        if isinstance(obj, cozmo.objects.LightCube):
            obj_input_dict['type'] = "cube"
            obj_input_dict['connected'] = obj.is_connected
            obj_input_dict['cube_id'] = obj.cube_id
            obj_input_dict['moving'] = obj.is_moving

        for input_name in obj_input_dict.keys():
            wme = self.WMEs.get(obj_designation + '.' + input_name)
            if wme is None:
                wme = psl.SoarWME(input_name, obj_input_dict[input_name])
                wme.add_to_wm(obj_wme)
                self.WMEs[obj_designation + '.' + input_name] = wme
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
        face_input_dict = {'expression': face.expression,
                           'expression_score': face.expression_score,
                           'face_id': face.face_id,
                           'name': face.name if face.name != '' else 'unknown',
                           'distance': obj_distance_factory(self.r, face)(),
                           'heading': obj_heading_factory(self.r, face)()
                           }
        for input_name in face_input_dict.keys():
            wme = self.WMEs.get(face_designation+'.'+input_name)
            if wme is None:
                wme = psl.SoarWME(input_name, face_input_dict[input_name])
                wme.add_to_wm(face_wme)
                self.WMEs[face_designation+'.'+input_name] = wme
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
            wme = self.WMEs.get(root_name+'.'+input_name)

            if not callable(new_val):
                if wme is None:
                    wme = root_id.CreateIdWME(input_name)
                    self.WMEs[root_name+'.'+input_name] = wme
                self.__input_recurse(new_val, root_name+'.'+input_name, wme)
                continue

            new_val = new_val()
            if wme is None:
                new_wme = psl.SoarWME(att=input_name,
                                      val=new_val)
                self.WMEs[root_name+'.'+input_name] = new_wme
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
