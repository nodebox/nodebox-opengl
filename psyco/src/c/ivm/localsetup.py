import os

dir = os.path.join(os.path.dirname(__file__), 'prolog')
for filename in os.listdir(dir):
    if filename.lower().endswith('.default'):
        basename = os.path.join(dir, filename[:-8])
        filename = os.path.join(dir, filename)
        if not os.path.exists(basename):
            copy = 2
        else:
            try:
                copy = os.stat(filename).st_mtime > os.stat(basename).st_mtime
            except OSError:
                copy = 0
        if copy:
            print 'Copying', filename, '->', basename
            if copy != 2:
                print '(OVERRIDING the older file)'
            import shutil
            shutil.copy(filename, basename)
