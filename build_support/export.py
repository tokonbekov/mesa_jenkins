"""handles synchronization of the build_root with the results directory"""
from . import run_batch_command
from . import Options
from . import ProjectMap

class Export:
    def __init__(self):
        # todo: provide wildcard mechanism
        pass

    def export(self):
        result_path = Options().result_path
        if not result_path:
            return

        cmd = ["cp", "-a", "-n",
               ProjectMap().build_root(), result_path]
        run_batch_command(cmd)

