from distutils.core import setup
from distutils.command.install_data import install_data


import glob
import os
import subprocess

import make_deb



setup (name = "okycmd", 
        version = make_deb.DEBVERSION,
        description = "Network client to onkyo receiver",
        author = "Olivier R-D",
        url = 'http://launchpad.net/onkyocmd',
        py_modules=["libonkyo"],
        license = "GNU General Public License",
        scripts = ["oky"]
        )


