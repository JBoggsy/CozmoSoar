from pysoarlib import *

from .WorldObject import WorldObject

import cozmo
from cozmo.objects import CustomObjectTypes as COT
boxes = [ COT.CustomType17,  COT.CustomType18, COT.CustomType19 ]

class WorldObjectManager(WMInterface):
    def __init__(self):
        WMInterface.__init__(self)

        self.objects = {}
        self.objs_to_remove = set()

        self.object_links = {}

        self.objects_id = None
        self.next_obj_id = 1
        self.wm_dirty = False

        self.svs_cmd_queue = []

    def get_object(self, handle):
        return self.objects.get(handle, None)

    def get_objects(self):
        return self.objects.values()

    def get_perception_id(self, handle):
        if handle in self.objects:
            return self.objects[handle].get_perception_id()
        return None

    def __str__(self):
        return "objects: {}".format(", ".join([ str(obj.get_perception_id()) for obj in self.objects.values() ]))

    def get_soar_handle(self, perc_id):
        return self.object_links.get(perc_id, perc_id)

    def link_objects(self, src_handle, dest_handle):
        self.object_links[src_handle] = dest_handle
        if src_handle in self.objects:
            wobj = self.objects[src_handle]
            self.objs_to_remove.append(wobj)
            del self.objects[src_handle]
            if dest_handle not in self.objects:
                self.objects[dest_handle] = wobj.copy(dest_handle)
        self.wm_dirty = True

    def update(self, cozmo_objs, localizer):
        linked_cozmo_objs = {}

        for cozmo_obj in cozmo_objs:
            if "object_type" in cozmo_obj.__dict__ and cozmo_obj.object_type not in boxes:
                continue
            if isinstance(cozmo_obj, cozmo.objects.Charger):
                continue
            perc_id = str(cozmo_obj.object_id)
            handle = self.get_soar_handle(perc_id)
            linked_cozmo_objs[handle] = cozmo_obj

        stale_objs = set(self.objects.keys())
        
        # For each object, either update existing or create if new
        for handle, cozmo_obj in linked_cozmo_objs.items():
            if handle in self.objects:
                wobj = self.objects[handle]
                wobj.update(cozmo_obj, localizer)
                stale_objs.remove(handle)
            else:
                self.objects[handle] = WorldObject(handle, cozmo_obj, localizer)

        # Remove all stale objects from WM
        for handle in stale_objs:
            self.objs_to_remove.add(self.objects[handle])
            del self.objects[handle]

        self.wm_dirty = True

    def get_svs_commands(self):
        q = self.svs_cmd_queue
        self.svs_cmd_queue = []
        return q

    #### METHODS TO UPDATE WORKING MEMORY ####
    def _add_to_wm_impl(self, parent_id):
        self.objects_id = parent_id.CreateIdWME("objects")
        for obj in self.objects.values():
            obj.add_to_wm(self.objects_id)
            self.svs_cmd_queue.extend(obj.get_svs_commands())

        self.wm_dirty = False

    def _update_wm_impl(self):
        if not self.is_added():
            return
        for obj in self.objects.values():
            obj.update_wm(self.objects_id)
            if obj in self.objs_to_remove:
                self.objs_to_remove.remove(obj)
            self.svs_cmd_queue.extend(obj.get_svs_commands())

        for obj in self.objs_to_remove:
            obj.remove_from_wm()
            self.svs_cmd_queue.extend(obj.get_svs_commands())

        self.objs_to_remove.clear()
        self.wm_dirty = False

    def _remove_from_wm_impl(self):
        for obj in self.objects.values():
            obj.remove_from_wm()
            self.svs_cmd_queue.extend(obj.get_svs_commands())
        for obj in self.objs_to_remove:
            obj.remove_from_wm()
            self.svs_cmd_queue.extend(obj.get_svs_commands())
        self.objs_to_remove.clear()

        self.objects_id.DestroyWME()
        self.objects_id = None
