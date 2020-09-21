import argparse
import sys
import os
import PySide2
from Bootstrapper import Bootstrapper, ApplicationMode
import logging

logger = logging.getLogger(__name__)

# Make sure the PySide2 plugin can be found:
dirname = os.path.dirname(PySide2.__file__)
plugin_path = os.path.join(dirname, 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

def main():
    parser = argparse.ArgumentParser(description="Metadata manager and automation tool.")
    appModeList = ', '.join(str(appMode) for appMode in list(ApplicationMode))
    parser.add_argument('-mode', metavar='Application Mode', type=ApplicationMode, default=ApplicationMode.Console,
                        choices=list(ApplicationMode), help=f"Application mode: {appModeList}")

    parser.add_argument('-task', metavar='Task Json File Path', type=str, default=None,
                        help=f"Path to a json file with task information.")

    args = parser.parse_args()
    bootstrapper = Bootstrapper(args.mode, args.task)
    status = bootstrapper.run()

    logger.info(f"Application closed with code {status}.")
    sys.exit(status)

if __name__ == "__main__":
    main()