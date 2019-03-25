import sys

from threading import Thread
import time

import Python_sml_ClientInterface as sml

from pysoarlib import SoarAgent, LanguageConnector

from .PerceptionConnector import PerceptionConnector
#from .RobotConnector import RobotConnector

class CozmoRosieAgent(SoarAgent):
    def __init__(self, config_filename=None, **kwargs):
        SoarAgent.__init__(self, config_filename=config_filename, verbose=False, **kwargs)

        self.connectors["language"] = LanguageConnector(self)
#        self.connectors["robot"] = RobotConnector(self)
        self.connectors["perception"] = PerceptionConnector(self)

