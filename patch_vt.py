import os
VER = 3.9

directory = '/root/.local/'
path = '/lib/python%s/site-packages/vt/utils.py' % VER
if not os.path.isfile(directory + path):
    path = 'env/' + path
else:
    path = directory + path

new_file = ''
with open(path, 'r') as f:
    for line in f:
        if 'run_until_complete' in line:
            line = '  return event_loop.create_task(future)'
        new_file += line

with open(path, 'w') as f:
    f.write(new_file)
