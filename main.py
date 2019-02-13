from time import sleep
import sys
import os
from os import path


import cozmo
from cozmo_soar import CozmoSoar, SoarObserver
import PySoarLib as psl

from mainGUI import GUI
from c_soar_util import *


def cozmo_soar_engine(robot: cozmo.robot):
    agent_name = "cozmo"
    agent = psl.SoarAgent(
        agent_name=agent_name,
        agent_source="productions/test-agent.soar",
        watch_level=1,
        write_to_stdout=True,
        print_handler=lambda s: print(GREEN_STR + s + RESET_STR),
    )

    cozmo_robot = CozmoSoar(agent, robot)
    for command in COZMO_COMMANDS:
        cozmo_robot.add_output_command(command)

    soar_observer = SoarObserver(agent)

    agent.add_connector("cozmo", cozmo_robot)
    agent.add_connector("observer", soar_observer)
    agent.connect()
    agent.start()
    # for i in range(25):
    #     agent.execute_command('step')
    #     sleep(1)
    while True:
        sleep(60)
    # agent.stop()


# def CozmoSoarEngine(robot: cozmo.robot.Robot):
#     kernel = sml.Kernel_CreateKernelInNewThread()
#     robot = CozmoSoar(robot, kernel, "Cozmo1")
#     agent = robot.agent
#     gui_root = tk.Tk()
#     gui = GUI(gui_root, robot.r, kernel, agent=agent)
#     # gui = None
#
#     callback = sync_world_factory(robot, agent, gui=gui)
#     agent.RegisterForRunEvent(sml.smlEVENT_AFTER_OUTPUT_PHASE,
#                               callback,
#                               None)
#     # agent.RegisterForPrintEvent(sml.smlEVENT_PRINT,
#     #                             soar_print_callback,
#     #                             None)
#     agent.LoadProductions("productions/test-agent.soar")
#     if agent.HadError():
#         print("Error loading productions: {}".format(agent.GetLastErrorDescription()))
#     agent.RunSelf(1)
#
#     # gui_root.mainloop()
#     i = 0
#     ready_to_continue = False
#     while True:
#         i += 1
#         agent.RunSelf(1)
#         if ready_to_continue:
#             sleep(0.25)
#         else:
#             ready_to_step = False
#             while not ready_to_step:
#                 command = input('>> ')
#                 if command.lower() in ['n', "next"]:
#                     ready_to_step = True
#                 elif command.lower() in ['c', "continue"]:
#                     ready_to_continue = True
#                     ready_to_step = True
#                 else:
#                     print(handle_soar_command(kernel, agent, command.strip()))
#
#
# def sync_world_factory(r: CozmoSoar, agent: sml.Agent, gui):
#     """
#     Create Soar cycle callback function for the given robot.
#
#     :return: A function to call when Soar leaves the output phase
#     """
#     def sync_world(*args, **kwargs):
#         # Update Soar via CozmoRobot object
#         print("Updating Soar")
#         r.update_input()
#
#         # Print Soar working memory to command line
#         print("State:")
#         print(agent.ExecuteCommandLine("print --depth 2 s1"))
#         print("Input link:")
#         print(agent.ExecuteCommandLine("print --depth 3 i2"))
#         print("Output link:")
#         print(agent.ExecuteCommandLine("print --depth 4 i3"))
#
#         # Update GUI environment values
#         if gui is not None:
#             print("Updating GUI")
#             gui.update_environment_inputs()
#
#         # Handle Soar output
#         print("Handling Soar Output")
#         numCommands = agent.GetNumberCommands()
#         for i in range(numCommands):
#             comm = agent.GetCommand(i)
#             try:
#                 print("Handling command {}".format(comm))
#                 r.handle_command(comm, agent)
#             except Exception as e:
#                 print("\u001b[31mError: ", e)
#                 print(e.args)
#                 print("\u001b[0m")
#                 raise e
#     return sync_world


# def handle_soar_command(kernel, agent, cmd):
#     """
#     When a user enters a Soar command, run it and print the result.
#
#     :param kernel: Soar kernel to run command in
#     :param agent: Soar agent the command is for
#     :param cmd: The command itself as a string
#     :return: The result of the command as a string
#     """
#     result = kernel.ExecuteCommandLine(cmd, agent.GetAgentName())
#     return result


# cozmo_soar_engine(None)
cozmo.run_program(cozmo_soar_engine)
