#import os
from subprocess import Popen

commands = ["python3 Scripts/build_tree.py -b", "python3 Scripts/search.py"] # hardcode the full path here or navigate to it's prefix before this step in the batch file
procs = [Popen(i) for i in commands if not print(i)]
for p in procs:
    p.wait()