import tkinter
import cv2
import PIL
import soar.Python_sml_ClientInterface as sml
import cozmo
from cozmo.camera import Camera
from cozmo.util import degrees, distance_mm, speed_mmps


def show_camera_img(robot):
    world = robot.world
    cam = robot.camera
    cam.color_image_enabled = True
    cam.image_stream_enabled = True

    while True:
        latest_img = world.latest_image
        if latest_img is None:
            continue
        raw_img = latest_img.raw_image
        raw_img.show()

cozmo.run_program(show_camera_img)