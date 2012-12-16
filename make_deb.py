#!/usr/bin/python2
"""
hackish file to crreate deb from setup.py
"""

import subprocess
from email.utils import formatdate
from bzrlib.branch import Branch

VERSION = "0.3"

def get_bzr_version():
    branch = Branch.open(".")
    rev = str(branch.revno())
    nick = branch.nick #This seems to only be the parent directory name
    bzrstring = "bzr" + rev
    return bzrstring



def get_changelog(progname, version, changelog, date):
    return """%s (%s) unstable; urgency=low

  %s 

 -- Olivier R-D <unknown@unknown>  %s """ % (progname, version, changelog, date)



def check_deb(name):
    print("checking if %s is installed" % name)
    subprocess.check_call("dpkg -s %s > /dev/null" % name, shell=True)

if __name__ == "__main__":
    check_deb("build-essential")
    f = open("debian/changelog", "w")
    f.write(get_changelog("onkyocmd", VERSION + get_bzr_version(), "Updated to last chnaes in bzr repository", formatdate()))
    f.close()

    #now build package
    subprocess.check_call("dpkg-buildpackage -rfakeroot -uc -us -b", shell=True)





