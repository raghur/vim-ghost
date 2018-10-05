import subprocess
import sys
from os import path
import os
import vim


def install():
    def isvim():
        return 'version' not in dir(vim)
    try:
        base = path.normpath(path.join(path.dirname(__file__), ".."))
        req = "requirements_win.txt" if sys.platform == "win32" else \
            "requirements_posix.txt"
        reqFile = path.join(base, req)
        print("ghost: installing dependencies from %s" % reqFile)
        py3 = sys.executable
        # on windows vim reports sys.executable as the path to gvim/vim
        if isvim() and sys.platform == "win32":
            py3 = path.normpath(path.join(os.__file__, "../..", "python.exe"))
        out = subprocess.check_output([py3,
                                       "-m", "pip", "install", "--user", "-r",
                                       reqFile], stderr=subprocess.STDOUT,
                                      shell=True)
        for l in out.decode().split(os.linesep):
            print("ghost: %s" % l)
        print("ghost: dependencies installed successfully")
    except subprocess.CalledProcessError as cpe:
        print("ghost: error installing dependencies: %s" % cpe)
