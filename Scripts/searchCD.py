import os
from subprocess import Popen

commands = ["python3 Scripts/build_tree.py -b", "python3 Scripts/search.py"]
procs = [Popen(i) for i in commands]

for p in procs:
    p.wait()  # Wait for each subprocess to finish
#print(os.listdir())
#subprocess.run(['python3', 'Scripts/build_tree.py', '-b'])
#subprocess.run(['python3', 'Scripts/search.py'])