import re
import cozmo

from pysoarlib import *

from .ObjectProperty import ObjectProperty

class CozmoObjectUnwrapper:
    def __init__(self, cozmo_obj):
        self.cozmo_obj = cozmo_obj

    def id(self):
        return self.cozmo_obj.object_id

    def name(self):
        return self.cozmo_obj.descriptive_name

    #def yaw(self):
    #    # Remapped so yaw=0 is down x-axis and yaw=90 is down y-axis
    #    return ((450 - int(self.cozmo_obj["rotation"]["y"])) % 360) * pi / 180.0

    def pos(self):
        pos = self.cozmo_obj.pose.position
        return [ pos.x/100.0, pos.y/100.0, pos.z/100.0 ]

    def rot(self):
        return [ 0.0, 0.0, self.cozmo_obj.pose.rotation.angle_z.radians ]

    def scl(self):
        return [ 0.25, 0.25, 0.25 ]

    def is_grabbable(self):
        return "grabbable1" if self.cozmo_obj.pickupable else "not-grabbable1"

    def is_light_cube(self):
        return isinstance(self.cozmo_obj, cozmo.objects.LightCube)

    def cube_id(self):
        return self.cozmo_obj.cube_id if self.is_light_cube() else None

    def is_connected(self):
        if self.is_light_cube():
            return "connected1" if self.cozmo_obj.is_connected else "not-connected1"
        return None

    def is_moving(self):
        if self.is_light_cube():
            return "moving1" if self.cozmo_obj.is_moving else "not-moving1"
        return None

    def color(self):
        cube_id = self.cube_id()
        if cube_id == None:
            return "white1"
        elif cube_id == 1:
            return "red1"
        elif cube_id == 2:
            return "green1"
        elif cube_id == 3:
            return "blue1"

class WorldObject(WMInterface):
    def __init__(self, handle, cozmo_obj=None):
        WMInterface.__init__(self)
        self.handle = handle
        self.objectId = cozmo_obj.object_id if cozmo_obj else None

        self.properties = {}

        self.bbox_pos = [0, 0, 0]
        self.bbox_rot = [0, 0, 0]
        self.bbox_scl = [0.1, 0.1, 0.1]

        self.pos_changed = True
        self.rot_changed = True
        self.scl_changed = True

        self.obj_id = None

        self.cozmo_obj = None
        if cozmo_obj:
            self.update(cozmo_obj)

        self.svs_cmd_queue = []

    def copy(self, new_handle):
        obj = WorldObject(new_handle)
        obj.objectId = self.objectId
        obj.set_pos(list(self.bbox_pos))
        obj.set_rot(list(self.bbox_rot))
        obj.set_scl(list(self.bbox_scl))
        for prop in self.properties:
            obj.properties[prop] = self.properties[prop].copy()
        return obj

    def get_handle(self):
        return self.handle

    def get_perception_id(self):
        return str(self.objectId)

    # Pos: The x,y,z world coordinate of the object
    def get_pos(self):
        return tuple(self.bbox_pos)
    def set_pos(self, pos):
        self.bbox_pos = [ pos[0], pos[1], pos[2] ]
        self.pos_changed = True

    # Rot: The orientation of the world object, in x,y,z axis rotations
    def get_rot(self):
        return tuple(self.bbox_rot)
    def set_rot(self, rot):
        self.bbox_rot = list(rot)
        self.rot_changed = True

    # Scl: The scale of the world object in x,y,z dims, scl=1.0 means width of 1 unit
    def get_scl(self):
        return tuple(self.bbox_scl)
    def set_scl(self, scl):
        self.bbox_scl = list(scl)
        self.scl_changed = True

    def update(self, cozmo_obj):
        self.cozmo_obj = cozmo_obj
        unwrapper = CozmoObjectUnwrapper(cozmo_obj)

        self.objectId = unwrapper.id()
        self.update_bbox(unwrapper)

        if len(self.properties) == 0:
            self.create_properties(unwrapper)

        if unwrapper.is_light_cube():
            self.properties["is-connected"].set_value(unwrapper.is_connected())
            self.properties["is-moving"].set_value(unwrapper.is_moving())

    def update_bbox(self, unwrapper):
        self.set_pos(unwrapper.pos())
        self.set_rot(unwrapper.rot())
        self.set_scl(unwrapper.scl())

    # Properties
    def create_properties(self, unwrapper):
        if unwrapper.is_light_cube():
            self.properties["category"] = ObjectProperty("category", "light-cube")
            self.properties["is-connected"] = ObjectProperty("is-connected1", unwrapper.is_connected())
            self.properties["is-moving"] = ObjectProperty("is-moving1", unwrapper.is_moving())
        else:
            self.properties["category"] = ObjectProperty("category", "object")

        self.properties["grabbable"] = ObjectProperty("is-grabbable1", unwrapper.is_grabbable())
        self.properties["color"] = ObjectProperty("color", unwrapper.color())
        self.properties["shape"] = ObjectProperty("shape", "cube1")

    ### Methods for managing working memory structures ###

    def get_svs_commands(self):
        q = self.svs_cmd_queue
        self.svs_cmd_queue = []
        return q

    def _add_to_wm_impl(self, parent_id):
        self.obj_id = parent_id.CreateIdWME("object")
        self.obj_id.CreateStringWME("object-handle", self.handle)

        for prop in self.properties.values():
            prop.add_to_wm(self.obj_id)

        self.svs_cmd_queue.append(SVSCommands.add_box(self.handle, self.bbox_pos, self.bbox_rot, self.bbox_scl))
        self.svs_cmd_queue.append(SVSCommands.add_tag(self.handle, "object-source", "perception"))

    def _update_wm_impl(self):
        if self.pos_changed:
            self.svs_cmd_queue.append(SVSCommands.change_pos(self.handle, self.bbox_pos))
            self.pos_changed = False

        if self.rot_changed:
            self.svs_cmd_queue.append(SVSCommands.change_rot(self.handle, self.bbox_rot))
            self.rot_changed = False

        if self.scl_changed:
            self.svs_cmd_queue.append(SVSCommands.change_scl(self.handle, self.bbox_scl))
            self.scl_changed = False

        for prop in self.properties.values():
            prop.update_wm()

    def _remove_from_wm_impl(self):
        self.svs_cmd_queue.append(SVSCommands.delete(self.handle))
        for prop in self.properties.values():
            prop.remove_from_wm()
        self.obj_id.DestroyWME()
        self.obj_id = None
