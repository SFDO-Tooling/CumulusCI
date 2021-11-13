import sys

import userpath

location = sys.argv[1]
if not userpath.in_current_path(location) and not userpath.in_new_path(location):
    userpath.append(location)
