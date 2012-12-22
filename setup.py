from distutils.core import setup
from distutils.command.install_data import install_data


import glob
import os
import subprocess

import make_deb



setup (name = "onkyocmd", 
        version = make_deb.bzrstring,
        description = "Network client to onkyo receiver",
        author = "Olivier R-D",
        url = 'http://launchpad.net/onkyocmd',
        py_modules=["onkyo"],
        license = "GNU General Public License",
        scripts = ["oky"]
        )


