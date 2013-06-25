from setuptools import setup
from distutils.command.install_data import install_data


import glob
import os
import subprocess

import make_deb



setup (name = "okycmd", 
        version = make_deb.DEBVERSION,
        description = "Network client to onkyo receiver",
        author = "Olivier R-D",
        url = 'https://github.com/oroulet/okycmd',
        py_modules=["libonkyo"],
        license = "GNU General Public License",
        entry_points = {'console_scripts': 
                ['oky = libonkyo:main']
                }
        )


