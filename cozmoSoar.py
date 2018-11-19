import soar.Python_sml_ClientInterface as sml
import cozmo
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
    def __init__(self, robot, agent):
        """
        Create a new `CozmoState` instance with the given robot and agent.

        :param robot: The Cozmo robot to interface with
        :param agent: The SML agent in Soar to communicate with
        """
        self.robot = robot
        self.agent = agent