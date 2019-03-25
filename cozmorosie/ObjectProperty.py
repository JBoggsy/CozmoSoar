from pysoarlib import *


class ObjectProperty(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.needs_update = True

        self.added = False
        self.root_id = None
        self.values_id = None
        self.value_wme = None

    def copy(self):
        return ObjectProperty(self.name, self.value)

    def set_value(self, value):
        if value != self.value:
            self.value = value
            self.needs_update = True

    ### Methods for managing working memory structures ###

    def is_added(self):
        return self.added

    def add_to_wm(self, parent_id):
        if self.added:
            return

        self.root_id = parent_id.CreateIdWME("property")
        self.root_id.CreateStringWME("property-handle", self.name)
        self.root_id.CreateStringWME("type", "visual")

        self.values_id = self.root_id.CreateIdWME("values")
        self.value_wme = self.values_id.CreateFloatWME(self.value, 1.0)
        
        self.added = True;
        self.needs_update = False

    def update_wm(self):
        if not self.added or not self.needs_update:
            return

        self.value_wme.DestroyWME()
        self.value_wme = self.values_id.CreateFloatWME(self.value, 1.0)
        self.needs_update = False

    def remove_from_wm(self):
        if not self.added:
            return

        self.root_id.DestroyWME()
        self.root_id = None
        self.values_id = None
        self.value_wme = None
        self.added = False
