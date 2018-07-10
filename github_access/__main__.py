import sys
import logging

from . import github
from . import dependabot

logging.basicConfig(level=logging.INFO)

failed = False


def handle_error(err):
    global failed
    logging.error(err)
    failed = True


github.repo_access(sys.argv[1:], handle_error)
# dependabot.add_repo(handle_error)

if failed:
    print('error(s) were encountered - see above', file=sys.stderr)
    sys.exit(1)
