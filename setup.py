from distutils.core import setup
from distutils.command.install_data import install_data


import glob
import os


from bzrlib.branch import Branch

branch = Branch.open(".")
rev = str(branch.revno())
nick = branch.nick
bzrstring = "bzr-" + nick + "-rev" + rev

setup (name = "onkyocmd", 
        version = bzrstring,
        description = "Network client to onkyo receiver",
        author = "Olivier R-D",
        url = 'http://launchpad.net/onkyocmd',
        py_modules=["onkyo"],
        #packages = ["onkyocmd"],
        #package_dir = {'icehms': 'src/python/icehms'},
        license = "GNU General Public License",
        
        scripts = ["oky"]


        )

            #("/var/lib/icehms/", ["db"]) ]
        #("bin", ["bin/cleaner_hms", "lsholons", "lstopics", "register_hms_services.py", "run_ice_servers.py", "update_hms_services"])



