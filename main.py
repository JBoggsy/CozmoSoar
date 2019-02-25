from time import sleep
from argparse import ArgumentParser
import os

import cozmo
from cozmo_soar import CozmoSoar, SoarObserver
import PySoarLib as psl

from c_soar_util import *


def cse_factory(agent_file, interactive=False):
    """Create the Cozmo program using the CLI arguments."""

    # Ensure the agent file exists
    if not os.path.isfile(agent_file):
        raise FileNotFoundError("ERROR: Agent file doesn't exist!")


    def cozmo_soar_engine(robot: cozmo.robot):
        agent_name = "cozmo"
        agent = psl.SoarAgent(
            agent_name=agent_name,
            agent_source=agent_file,
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


def gen_cli_parser():
    cli_parser = ArgumentParser(description="Run a Soar agent in a Cozmo robot.")
    cli_parser.add_argument(
        "-i",
        "--interactive",
        dest="interactive",
        help="If present, the interface will run in interactive mode.",
        action="store_true",
    )
    cli_parser.add_argument("agent")
    return cli_parser


if __name__ == "__main__":
    cli_parser = gen_cli_parser()
    args = cli_parser.parse_args()
    cse = cse_factory(args.agent, args.interactive)
    cozmo.run_program(cse)
