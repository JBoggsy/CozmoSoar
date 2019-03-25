from pysoarlib import WMInterface

from .WorldObject import WorldObject

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

    def get_soar_handle(self, perc_id):
        return self.object_links.get(perc_id, None)

    def link_objects(self, src_handle, dest_handle):
        self.object_links[src_handle] = dest_handle
        if src_handle in self.objects:
            wobj = self.objects[src_handle]
            self.objs_to_remove.append(wobj)
            del self.objects[src_handle]
            if dest_handle not in self.objects:
                self.objects[dest_handle] = wobj.copy(dest_handle)
        self.wm_dirty = True

    def update(self, world_data):
        new_obj_data = {}

        for obj_data in world_data:
            perc_id = obj_data.object_id
            handle = self.object_links.get(perc_id, perc_id)
            new_obj_data[handle] = obj_data

        stale_objs = set(self.objects.keys())
        
        # For each object, either update existing or create if new
        for handle, obj_data in new_obj_data.items():
            if handle in self.objects:
                wobj = self.objects[handle]
                wobj.update(obj_data)
                stale_objs.remove(handle)
            else:
                self.objects[handle] = WorldObject(handle, obj_data)

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
