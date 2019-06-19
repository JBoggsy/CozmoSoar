from time import sleep
from argparse import ArgumentParser
from pathlib import Path
import os

import cozmo
from cozmo_soar import CozmoSoar
import PySoarLib as psl

from c_soar_util import *


def cse_factory(agent_file: Path, auto_run=False, object_file=None, debugger=False):
    """Create the Cozmo program using the CLI arguments."""
    def cozmo_soar_engine(robot: cozmo.robot):
        agent_name = "cozmo"
        agent = psl.SoarAgent(
            agent_name=agent_name,
            agent_source=str(agent_file.absolute()).replace("\\", "\\\\"),
            watch_level=1,
            write_to_stdout=True,
            print_handler=lambda s: print(GREEN_STR + s + RESET_STR),
            spawn_debugger=debugger
        )

        cozmo_robot = CozmoSoar(agent, robot, object_file)
        for command in COZMO_COMMANDS:
            cozmo_robot.add_output_command(command)

        agent.add_connector("cozmo", cozmo_robot)
        agent.connect()
        agent.execute_command("svs --enable")
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

    cli_parser.add_argument(
        "-d",
        "--debugger",
        dest="debugger",
        help="If present, will launch the Java soar debugger as long as it is in your SOAR_HOME.",
        action="store_true"
    )

    cli_parser.add_argument(
        "--3d-view",
        dest="debugger",
        help="If present, open the 3D viewer.",
        action="store_true"
    )
    cli_parser.add_argument(
        "-nv",
        "--no-viewer",
        dest="no_viewer",
        help="If present, will not launch the viewer.",
        action="store_false"
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
    print(args.debugger)
    cse = cse_factory(agent_file_path, args.autorun, args.obj_file, args.debugger)
    cozmo.run_program(cse, use_3d_viewer=False, use_viewer=args.no_viewer)
