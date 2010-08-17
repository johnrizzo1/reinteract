#!/usr/bin/env python
#
# Copyright 2007-2009 Owen Taylor
#
# This file is part of Reinteract and distributed under the terms
# of the BSD license. See the file COPYING in the Reinteract
# distribution for full details.
#
########################################################################

from reinteract.global_settings import global_settings
import os
import reinteract.main
import sys

script_path = os.path.realpath(os.path.abspath(sys.argv[0]))
topdir = os.path.dirname(os.path.dirname(script_path))
libdir = os.path.join(topdir, 'python')
externaldir = os.path.join(topdir, 'external')
builderdir = os.path.join(topdir, 'dialogs')
examplesdir = os.path.join(topdir, 'examples')
helpdir = os.path.join(topdir, 'help')

icon_file = os.path.join(topdir, 'Reinteract.ico')
if not os.path.isfile(icon_file): #Added so that everything works even in development
    icon_file = os.path.join(topdir + os.path.sep +  "data" + os.path.sep + "Reinteract.ico")

sys.path[0:0] = [libdir, externaldir]

global_settings.dialogs_dir = builderdir
global_settings.examples_dir = examplesdir
global_settings.icon_file = icon_file
global_settings.version = "@VERSION@"

reinteract.main.main()
