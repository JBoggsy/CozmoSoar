from time import sleep
from argparse import ArgumentParser
from pathlib import Path
import os

import cozmo
from cozmo_soar import CozmoSoar, SoarObserver
import PySoarLib as psl

from c_soar_util import *


def cse_factory(agent_file: Path, auto_run=False, object_file=None):
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

        cozmo_robot = CozmoSoar(agent, robot, object_file)
        for command in COZMO_COMMANDS:
            cozmo_robot.add_output_command(command)

        soar_observer = SoarObserver(agent)

        agent.add_connector("cozmo", cozmo_robot)
        # agent.add_connector("observer", soar_observer)
        agent.connect()
        if not auto_run:
            while True:
                agent.execute_command(input(">> "))
        else:
            agent.start()
            while True:
                sleep(60)
            agent.stop()

    return cozmo_soar_engine


def gen_cli_parser():
    cli_parser = ArgumentParser(description="Run a Soar agent in a Cozmo robot.")
    cli_parser.add_argument(
        "-r",
        "--run",
        dest="autorun",
        help="If present, the interface will run without prompting for input.",
        action="store_true",
    )

    cli_parser.add_argument(
        "-o",
        "--objects",
        dest="obj_file",
        help="If present, points to an XML file defining custom objects for an environment."
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
    cse = cse_factory(agent_file_path, args.autorun, args.obj_file)
    cozmo.run_program(cse)
