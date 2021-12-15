import hook
from ApplicationMode import ApplicationMode
import argparse
import sys
import os
import PySide2
from Bootstrapper import Bootstrapper
import logging
import subprocess

logging.getLogger('comtypes').setLevel('WARNING')

logger = logging.getLogger(__name__)

# Make sure the PySide2 plugin can be found:
dirname = os.path.dirname(PySide2.__file__)
plugin_path = os.path.join(dirname, 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

def main():
    parser = argparse.ArgumentParser(description="Metadata manager and automation tool.")
    appModeList = ', '.join(str(appMode) for appMode in list(ApplicationMode))
    parser.add_argument('-mode', metavar='Application Mode', type=ApplicationMode, default=ApplicationMode.GUI,
                        choices=list(ApplicationMode), help=f"Application mode: {appModeList}")

    parser.add_argument('-task', metavar='Task Json File Path', type=str, default=None,
                        help=f"Path to a json file with task information.")

    parser.add_argument('-launcher', help='Path to the launcher.', type=str, default=None)

    args = parser.parse_args()
    bootstrapper = Bootstrapper(args.mode, args.task, args.launcher)
    status = bootstrapper.run()

    if bootstrapper.restartRequested and args.launcher:
        logger.info(f'Opening launcher: {args.launcher}')
        os.chdir(os.path.dirname(args.launcher))
        subprocess.Popen([args.launcher])

    logger.info(f"Application closed with code {status}.")
    sys.exit(status)

if __name__ == "__main__":
    main()