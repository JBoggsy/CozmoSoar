from pysoarlib import *
import re

from .ObjectProperty import ObjectProperty

class ObjectDataUnwrapper(WMInterface):
    def __init__(self, data):
        WMInterface.__init__(self)
        self.data = data

    def id(self):
        return str(self.data["objectId"])

    def name(self):
        return re.match(r"[a-zA-Z]*", self.id()).group(0).lower()

    #def yaw(self):
    #    # Remapped so yaw=0 is down x-axis and yaw=90 is down y-axis
    #    return ((450 - int(self.data["rotation"]["y"])) % 360) * pi / 180.0

    def pos(self):
        # Swap y and z axes
        b = self.data["bounds3D"]
        [x, z, y] = [ (float(b[d+3]) + float(b[d]))/2 for d in range(0, 3) ]
        return [x, y, z]

    def rot(self):
        return ( 0.0, 0.0, 0.0 )

    def scl(self):
        b = self.data["bounds3D"]
        [x, z, y] = [ (float(b[d+3]) - float(b[d])) for d in range(0, 3) ]
        return [x, y, z]

    def is_grabbable(self):
        return self.data.pickupable

    def is_moving(self):
        return sefl.data.is_moving


class WorldObject(object):
    def __init__(self, handle, obj_data=None):
        self.handle = handle
        self.objectId = obj_data["objectId"] if obj_data else None

        self.properties = {}

        self.bbox_pos = [0, 0, 0]
        self.bbox_rot = [0, 0, 0]
        self.bbox_scl = [0.1, 0.1, 0.1]

        self.pos_changed = True
        self.rot_changed = True
        self.scl_changed = True

        self.obj_id = None

        if obj_data:
            self.update(obj_data)

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

    def update(self, obj_data):
        unwrapper = ObjectDataUnwrapper(obj_data)

        self.objectId = unwrapper.id()
        self.update_bbox(unwrapper)

        self.properties["moving"].set_value( "true" if unwrapper.is_moving() else "false" )

    def update_bbox(self, unwrapper):
        self.set_pos(unwrapper.pos())
        self.set_rot(unwrapper.rot())
        self.set_scl(unwrapper.scl())

    # Properties
    def create_properties(self, unwrapper):
        self.properties["category"] = ObjectProperty("category", "object")

        if unwrapper.is_grabbable():
            self.properties["grabbable"] = ObjectProperty("is-grabbable1", "grabbable1")

        self.properties["moving"] = ObjectProperty("moving", "false")


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
