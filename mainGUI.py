
import sys
import cozmo
from cozmo.robot import EvtRobotStateUpdated

import cv2
from tkinter import *
sys.path.append('/Users/nickmatton/Desktop/Soar/Soar/out/')
import soar.Python_sml_ClientInterface as sml

class GUI:
    def __init__(self, master, robot: cozmo.robot.Robot, kernel, agent=None):
        self.robot = robot
        self.kernel = kernel
        self.master = master
        self.run = False
        #self.robot.world.add_event_handler(EvtRobotStateUpdated, self.update_environment_inputs)
        if agent is None:
            self.agent = self.kernel.CreateAgent("agent")
        else:
            self.agent = agent
        if not self.agent:
            print("Error creating agent: " + kernel.GetLastErrorDescription())
            exit(1)
        #
        #This part pretty much just creates labels to output all the values needed
        #
        self.master.title("CozmoSoar")

        self.label1 = Label(master, text="Soar Command")
        self.label1.grid(row=0)

        self.entry1 = Entry(master)
        self.entry1.grid(row=0, column=1)

        self.send_command_button = Button(self.master, text="Send Command", command=self.send_command)
        self.send_command_button.grid(row=1)
        
        self.step_button = Button(self.master, text="Step", command=self.step)
        self.step_button.grid(row=1, column=1)
        
        self.run_button = Button(self.master, text="Run", command=self.run)
        self.run_button.grid(row=1, column=2)
        
        self.stop_button = Button(self.master, text="Stop", command=self.stop)
        self.stop_button.grid(row=1, column=3)
        
        self.label2 = Label(master, text="Num steps to run:")
        self.label2.grid(row=2)
        
        self.entry2 = Entry(master)
        self.entry2.grid(row=2, column=1)

        self.update_environment_inputs_button = Button(self.master, text="Update env inputs", command=self.update_environment_inputs)
        self.update_environment_inputs_button.grid(row=2)

        self.close_button = Button(self.master, text="Close", command=self.master.quit)
        self.close_button.grid(row=100)

        self.bat_volt_label = Label(self.master, text="Battery Voltage: ")
        self.bat_volt_label.grid(row=3, column=0)

        self.bat_volt = Label(self.master, text=round(self.robot.battery_voltage, 3))
        self.bat_volt.grid(row=3, column=1)

        self.is_carrying_label = Label(self.master, text="Carrying Block: ")
        self.is_carrying_label.grid(row=5, column=0)

        self.is_carrying = Label(self.master, text=self.robot.is_carrying_block)
        self.is_carrying.grid(row=5, column=1)

        self.carrying_block_id_label = Label(self.master, text="Carrying Block ID: ")
        self.carrying_block_id_label.grid(row=6, column=0)

        self.carrying_block_id = Label(self.master, text=self.robot.carrying_object_id)
        self.carrying_block_id.grid(row=6, column=1)

        self.is_charging_label = Label(self.master, text="Is Charging: ")
        self.is_charging_label.grid(row=7, column=0)

        self.is_charging = Label(self.master, text=self.robot.is_charging)
        self.is_charging.grid(row=7, column=1)

        self.is_cliff_detected_label = Label(self.master, text="Is Cliff Detected: ")
        self.is_cliff_detected_label.grid(row=8, column=0)

        self.is_cliff_detected = Label(self.master, text=self.robot.is_cliff_detected)
        self.is_cliff_detected.grid(row=8, column=1)

        self.head_angle_label = Label(self.master, text="Head Angle: ")
        self.head_angle_label.grid(row=9, column=0)

        self.head_angle = Label(self.master, text=self.robot.head_angle)
        self.head_angle.grid(row=9, column=1)

        self.lift_angle_label = Label(self.master, text="Lift Angle: ")
        self.lift_angle_label.grid(row=10, column=0)

        self.lift_angle = Label(self.master, text=self.robot.lift_angle)
        self.lift_angle.grid(row=10, column=1)

        self.lift_height_label = Label(self.master, text="Lift Height: ")
        self.lift_height_label.grid(row=11, column=0)

        self.lift_height = Label(self.master, text=self.robot.lift_height)
        self.lift_height.grid(row=11, column=1)

        self.lift_ratio_label = Label(self.master, text="Lift Ratio: ")
        self.lift_ratio_label.grid(row=12, column=0)

        self.lift_ratio = Label(self.master, text=self.robot.lift_ratio)
        self.lift_ratio.grid(row=12, column=1)

        self.is_picked_up_label = Label(self.master, text="Is Picked Up: ")
        self.is_picked_up_label.grid(row=13, column=0)

        self.is_picked_up = Label(self.master, text=self.robot.is_picked_up)
        self.is_picked_up.grid(row=13, column=1)

        self.pose_label = Label(self.master, text="Pose: ")
        self.pose_label.grid(row=14, column=0)

        self.pose = Label(self.master, text=self.robot.is_picked_up)
        self.pose.grid(row=14, column=1)

        self.gyro_label = Label(self.master, text="Gryo: ")
        self.gyro_label.grid(row=15, column=0)

        self.gyro = Label(self.master, text=self.robot.gyro)
        self.gyro.grid(row=15, column=1)

        self.robot_id_label = Label(self.master, text="Robot ID: ")
        self.robot_id_label.grid(row=16, column=0)

        self.robot_id = Label(self.master, text=self.robot.robot_id)
        self.robot_id.grid(row=16, column=1)

        self.serial_label = Label(self.master, text="Serial: ")
        self.serial_label.grid(row=17, column=0)

        self.serial = Label(self.master, text=self.robot.serial)
        self.serial.grid(row=17, column=1)

        #
        # camera display
        #
        self.panel = Label(self.master)
        self.panel.grid(row=0, column=10)
        self.vs = cv2.VideoCapture(0)
        self.output_path = "./"
        self.current_image = NONE
        self.video_loop()
    
    def stop(self):
        #stop
        self.run = False
            #cmd = "stop"
            #print(self.agent.ExecuteCommandLine(cmd).strip())
        
    def run(self):
        # run
        cmd = "step"
        self.run = True
        while(self.run):
            print(self.agent.ExecuteCommandLine(cmd).strip())
    
    def step(self):
        # step and update
        cmd = "step"
        print(self.agent.ExecuteCommandLine(cmd).strip())
        self.update_environment_inputs()
    
    def run_x_steps(self):
        x = self.entry2.get()
        cmd = "step"
        for i in range(int(x)):
            print(self.agent.ExecuteCommandLine(cmd).strip())
    
    def send_command(self):
        # sends commands to soar
        cmd = self.entry1.get()
        print(self.agent.ExecuteCommandLine(cmd).strip())


    def update_environment_inputs(self):
        #
        # This just updates all the values
        # that are recieved by the cozmo
        #

        self.bat_volt = Label(self.master, text=round(self.robot.battery_voltage, 3))
        self.bat_volt.grid(row=3, column=1)

        self.is_carrying = Label(self.master, text=self.robot.is_carrying_block)
        self.is_carrying.grid(row=5, column=1)

        self.carrying_block_id = Label(self.master, text=self.robot.carrying_object_id)
        self.carrying_block_id.grid(row=6, column=1)

        self.is_charging = Label(self.master, text=self.robot.is_charging)
        self.is_charging.grid(row=7, column=1)

        self.is_cliff_detected = Label(self.master, text=self.robot.is_cliff_detected)
        self.is_cliff_detected.grid(row=8, column=1)

        self.head_angle = Label(self.master, text=self.robot.head_angle)
        self.head_angle.grid(row=9, column=1)

        self.lift_angle = Label(self.master, text=self.robot.lift_angle)
        self.lift_angle.grid(row=10, column=1)

        self.lift_height = Label(self.master, text=self.robot.lift_height)
        self.lift_height.grid(row=11, column=1)

        self.lift_ratio = Label(self.master, text=self.robot.lift_ratio)
        self.lift_ratio.grid(row=12, column=1)

        self.is_picked_up = Label(self.master, text=self.robot.is_picked_up)
        self.is_picked_up.grid(row=13, column=1)

        self.pose = Label(self.master, text=self.robot.is_picked_up)
        self.pose.grid(row=14, column=1)

        self.gyro = Label(self.master, text=self.robot.gyro)
        self.gyro.grid(row=15, column=1)

        self.robot_id = Label(self.master, text=self.robot.robot_id)
        self.robot_id.grid(row=16, column=1)

        self.serial = Label(self.master, text=self.robot.serial)
        self.serial.grid(row=17, column=1)

        self.panel = Label(self.master)
        self.panel.grid(row=0, column=5)

        self.master.update()
        print("environment updated")

    def video_loop(self):
        ok, frame = self.vs.read()
        if ok:
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            cv2.imshow('frame', cv2image)

        self.master.after(100, self.video_loop)


def cozmo_program(robot: cozmo.robot.Robot):
    master = Tk()
    kernel = sml.Kernel.CreateKernelInNewThread()
    if not kernel or kernel.HadError():
        print("Error creating kernal: " + kernel.GetLastErrorDescription())
        exit(1);

    my_gui = GUI(master, robot, kernel)
    master.mainloop()


if __name__ == '__main__':
    cozmo.run_program(cozmo_program)
