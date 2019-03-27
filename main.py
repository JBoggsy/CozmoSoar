from time import sleep
from argparse import ArgumentParser
from pathlib import Path
import os

import cozmo
from cozmo_soar import CozmoSoar, SoarObserver
import PySoarLib as psl

from c_soar_util import *

from cozmorosie.ChatGUI import ChatGUI

from tkinter import *

def cse_factory(agent_file: Path, interactive=False):
    """Create the Cozmo program using the CLI arguments."""
    def cozmo_soar_engine(robot: cozmo.robot):
        agent_name = "cozmo"
        agent = psl.SoarAgent(
            agent_name=agent_name,
            agent_source=str(agent_file.absolute()).replace("\\", "\\\\"),
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
        if interactive:
            for i in range(25):
                agent.execute_command(input(">> "))
        else:
            agent.start()
            while True:
                sleep(60)
            agent.stop()

    return cozmo_soar_engine

def cre_factory(rosie_config_file: Path):
    """Create the Cozmo program using the CLI arguments."""
    def cozmo_rosie_engine(robot: cozmo.robot):
        agent_name = "cozmo"
        agent = psl.SoarAgent(
            agent_name=agent_name,
            config_filename = str(rosie_config_file.absolute()).replace("\\", "\\\\"),
        )

        cozmo_robot = CozmoSoar(agent, robot)
        for command in COZMO_COMMANDS:
            cozmo_robot.add_output_command(command)

        #soar_observer = SoarObserver(agent)

        agent.add_connector("cozmo", cozmo_robot)
        #agent.add_connector("observer", soar_observer)

        root = Tk()
        chat_gui = ChatGUI(agent, master=root)
        def shutdown():
            agent.kill()
            root.destroy()
        root.protocol("WM_DELETE_WINDOW", shutdown)
        agent.connect()
        root.mainloop()

    return cozmo_rosie_engine


def gen_cli_parser():
    cli_parser = ArgumentParser(description="Run a Soar agent in a Cozmo robot.")
    cli_parser.add_argument(
        "-i",
        "--interactive",
        dest="interactive",
        help="If present, the interface will run in interactive mode.",
        action="store_true",
    )
    cli_parser.add_argument(
        "-r", 
        "--rosie",
        dest="rosie",
        help="If present, it will run the rosie agent with a chat window",
        action="store_true",
    )
    cli_parser.add_argument("agent")
    return cli_parser


if __name__ == "__main__":
    cli_parser = gen_cli_parser()
    args = cli_parser.parse_args()
    agent_file_path = Path(args.agent)
    if not agent_file_path.is_file():
        raise FileNotFoundError("ERROR: Agent file doesn't exist!")
    else:
        print("Sourcing from file {}".format(agent_file_path.absolute()))

    if args.rosie:
        prog = cre_factory(agent_file_path)
    else:
        prog = cse_factory(agent_file_path, args.interactive)

    cozmo.run_program(prog)
