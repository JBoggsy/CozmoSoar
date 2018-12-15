from time import sleep
from threading import current_thread

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

    callback = sync_world_factory(robot, agent)
    agent.RegisterForRunEvent(sml.smlEVENT_AFTER_OUTPUT_PHASE,
                              callback,
                              None)

    agent.RegisterForPrintEvent(sml.smlEVENT_PRINT,
                                soar_print_callback,
                                None)

    agent.LoadProductions("productions/test-agent.soar")
    if agent.HadError():
        print("Error loading productions: {}".format(agent.GetLastErrorDescription()))

    i = 0
    ready_to_continue = False
    while True:
        i += 1
        agent.RunSelf(1)
        print("\n", i)
        print("State:")
        print(kernel.ExecuteCommandLine("print --depth 2 s1", agent.GetAgentName()))
        print("Input link:")
        print(kernel.ExecuteCommandLine("print --depth 3 i2", agent.GetAgentName()))
        print("Output link:")
        print(kernel.ExecuteCommandLine("print --depth 4 i3", agent.GetAgentName()))

        if ready_to_continue:
            sleep(0.25)
        else:
            ready_to_step = False
            while not ready_to_step:
                command = input('>> ')
                if command.lower() in ['n', "next"]:
                    ready_to_step = True
                elif command.lower() in ['c', "continue"]:
                    ready_to_continue = True
                    ready_to_step = True
                else:
                    print(handle_soar_command(kernel, agent, command.strip()))


def sync_world_factory(r: CozmoSoar, agent: sml.Agent):
    """
    Create callback function for the given robot.

    :return: A function to call when Soar leaves the output phase
    """
    def sync_world(*args, **kwargs):
        r.update_input()
        numCommands = agent.GetNumberCommands()
        for i in range(numCommands):
            comm = agent.GetCommand(i)
            try:
                r.handle_command(comm, agent)
            except Exception as e:
                print("\u001b[31mError: ", e)
                print(e.args)
                print("\u001b[0m")
                raise e
    return sync_world


def soar_print_callback(id, user_data, agent: sml.Agent, message):
    print("\u001b[32m {}: {} \u001b[0m".format(agent.GetAgentName(), message))


def handle_soar_command(kernel, agent, cmd):
    """
    When a user enters a Soar command, run it and print the result.

    :param kernel: Soar kernel to run command in
    :param agent: Soar agent the command is for
    :param cmd: The command itself as a string
    :return: The result of the command as a string
    """
    result = kernel.ExecuteCommandLine(cmd, agent.GetAgentName())
    return result


cozmo.run_program(CozmoSoarEngine)
