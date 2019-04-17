from tkinter import *
from PIL import Image, ImageTk
import cozmo

from threading import Lock

def on_new_camera_image(evt, image, **kwargs):
    raw = image.raw_image

class CameraView(Toplevel):
    def __init__(self, cozmo_robot, master=None):
        Toplevel.__init__(self, master)
        self.lock = Lock()
        self.canvas = Canvas(self, width=400, height=300)
        self.canvas.pack()
        cozmo_robot.world.image_annotator.enable_annotator('objects')
        cozmo_robot.world.add_event_handler(cozmo.world.EvtNewCameraImage, lambda evt,image,**kwargs: self.camera_image = image.annotate_image())
        self.camera_image = None
        self.canvas_image = None
        self.after(200, lambda: self.update_image())

    def update_image(self):
        img = self.camera_image
        if img:
            self.image_tk = ImageTk.PhotoImage(img)
            if not self.canvas_image:
                self.canvas_image = self.canvas.create_image(200, 150, image=self.image_tk)
            else:
                self.canvas.itemconfig(self.canvas_image, image=self.image_tk)
        self.after(200, lambda: self.update_image())

    #self.bind("t", lambda e : do stuff)


    #def create_buttons(self):
    #    turn_left = Button(self, text="L")
    #    turn_left["command"] = lambda : self.sim_robot.exec_simple_command("RotateLeft")
    #    self.buttons.append(turn_left)
    #    self.buttons[i].grid(row=int(i/4), column=i%4, sticky=N+S+E+W)

    #def create_menu(self):
    #    self.menu_label_var = StringVar()
    #    self.menu_label = Label(self, textvariable=self.menu_label_var)
    #    self.menu_label.grid(row=4, columnspan=4, sticky=W+E)

    #    self.menu_buttons = []

    #def show_menu(self, name, options):
    #    if len(options) == 0:
    #        return
    #    self.menu_label_var.set(name)
    #    for opt in options:
    #        self.menu_buttons.append(Button(self, text=opt, command=lambda opt=opt: self.on_menu_select(opt, name)))
    #    for r, btn in enumerate(self.menu_buttons):
    #        btn.grid(row=5+r, columnspan=4, sticky=W+E)

    #def on_menu_select(self, opt, cmd_name):
    #    self.hide_menu()
    #    self.handle_command(cmd_name, opt)
