import sys
import os

from . import main

main(sys.argv[1:], os.environ['GITHUB_TOKEN'])
