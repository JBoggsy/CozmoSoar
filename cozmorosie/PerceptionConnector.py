import sys
from threading import Lock

from pysoarlib import *

from .WorldObjectManager import WorldObjectManager


class PerceptionConnector(AgentConnector):
    def __init__(self, agent):
        AgentConnector.__init__(self, agent)
        self.add_output_command("modify-scene")
        self.objects = WorldObjectManager()
        self.wm_dirty = True
        self.lock = Lock()

    def on_input_phase(self, input_link):
        if not self.wm_dirty:
            return
        self.lock.acquire()
        self.objects.update_wm(input_link)
        svs_commands = self.objects.get_svs_commands()
        self.lock.release()
        self.wm_dirty = False
        if len(svs_commands) > 0:
            self.agent.agent.SendSVSInput("\n".join(svs_commands))

    def handle_world_change(self, world):
        self.lock.acquire()
        self.objects.update(world)
        self.wm_dirty = True
        self.lock.release()

    def on_init_soar(self):
        self.lock.acquire()
        self.objects.remove_from_wm()
        svs_commands = self.objects.get_svs_commands()
        self.lock.release()
        if len(svs_commands) > 0:
            self.agent.agent.SendSVSInput("\n".join(svs_commands))

    def on_output_event(self, command_name, root_id):
        if command_name == "modify-scene":
            self.process_modify_scene_command(root_id)
    
    def process_modify_scene_command(self, root_id):
        error = False
        mod_type = root_id.GetChildString("type")
        if mod_type == "link":
            src_handle = root_id.GetChildString("source-handle")
            dest_handle = root_id.GetChildString("destination-handle")
            if src_handle == None:
                error = True
                self.print_handler("!!! PerceptionConnector::process_modify_scene_command[link]\n  No ^source-handle")
            elif dest_handle == None:
                error = True
                self.print_handler("!!! PerceptionConnector::process_modify_scene_command[link]\n  No ^destination-handle")
            else:
                self.lock.acquire()
                self.objects.link_objects(src_handle, dest_handle)
                self.lock.release()
        else:
            error = True
            self.print_handler("!!! PerceptionConnector::process_modify_scene_command\n  Bad ^type")

        root_id.CreateStringWME("status", "error" if error else "complete")
