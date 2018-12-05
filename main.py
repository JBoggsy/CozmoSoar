from time import sleep

import tkinter
import cv2
import PIL
import soar.Python_sml_ClientInterface as sml
import cozmo
from cozmo.camera import Camera
from cozmo.util import degrees, distance_mm, speed_mmps
from cozmo_soar import CozmoSoar


def CozmoSoarEngine(robot: cozmo.robot.Robot):
    kernel = sml.Kernel_CreateKernelInNewThread()
    robot = CozmoSoar(robot, kernel, "Cozmo1")
    agent = robot.agent

    def update_in_link(*args, **kwargs):
        robot.update_input()
        print("Input link:")
        print(kernel.ExecuteCommandLine("print --depth 3 i2", agent.GetAgentName()))

    agent.RegisterForRunEvent(sml.smlEVENT_AFTER_OUTPUT_PHASE, update_in_link, None)

    agent.RunSelfTilOutput()
    # while True:
    #     pass



cozmo.run_program(CozmoSoarEngine)
