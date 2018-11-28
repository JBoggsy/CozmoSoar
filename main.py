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
    while True:
        robot.agent.RunSelf(1)
        print("State:")
        print(kernel.ExecuteCommandLine("print <s>", robot.name))
        print("=====\nInput-link:")
        print(kernel.ExecuteCommandLine("print --depth 2 i2", robot.name))
        robot.update_input()
        input()


cozmo.run_program(CozmoSoarEngine)
