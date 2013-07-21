#!/usr/bin/python3
"""
hackish file to crreate deb from setup.py
"""

import subprocess
from email.utils import formatdate

DEBVERSION = "0.8"


def get_changelog(progname, version, changelog, date):
    """
    return a dummy changelog acceptable by debian script engine
    """
    return """%s (%s) unstable; urgency=low

  %s 

 -- Olivier R-D <unknown@unknown>  %s """ % (progname, version, changelog, date)



def check_deb(name):
    print("checking if %s is installed" % name)
    subprocess.check_call("dpkg -s %s > /dev/null" % name, shell=True)

if __name__ == "__main__":
    check_deb("build-essential")
    f = open("debian/changelog", "w")
    f.write(get_changelog("okycmd", DEBVERSION , "Updated to last changes in repository", formatdate()))
    f.close()

    #now build package
    #subprocess.check_call("dpkg-buildpackage -rfakeroot -uc -us -b", shell=True)
    subprocess.check_call("fakeroot dh binary --with python3 --without python2,python-support,python-central", shell=True)
    #subprocess.check_call("fakeroot dh binary --with python3", shell=True)
    subprocess.check_call("dh clean", shell=True)





