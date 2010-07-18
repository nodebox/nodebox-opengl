import sys, os

def data2unix(lines):
    data = []
    modif = 0
    for line in lines:
        line1 = line.replace('\r', '')
        modif = modif + (line!=line1)
        data.append(line1)
    return data, modif

def data2win(lines):
    data = []
    modif = 0
    for line in lines:
        if line[-1:] == '\n':
            line1 = line[:-1].replace('\r', '') + '\r\n'
            modif = modif + (line!=line1)
        data.append(line1)
    return data, modif

def file2unix(name, verbose=1):
    "Turn a file's end-of-line into Unix flavor without changing the timestamp."
    s = os.stat(name)
    f = open(name, 'rb')
    data, modif = data2unix(f)
    f.close()
    if modif:
        if verbose:
            print "Unix'ed %d lines in %s" % (modif, name)
        f = open(name, 'wb')
        f.writelines(data)
        f.close()
    os.utime(name, (s.st_atime, s.st_mtime))
    return modif

def file2win(name, verbose=1):
    "Turn a file's end-of-line into Windows flavor without changing the timestamp."
    s = os.stat(name)
    f = open(name, 'rb')
    data, modif = data2win(f)
    f.close()
    if modif:
        if verbose:
            print "Win'ed %d lines in %s" % (modif, name)
        f = open(name, 'wb')
        f.writelines(data)
        f.close()
    os.utime(name, (s.st_atime, s.st_mtime))
    return modif

class Directory:
    def __init__(self, srcpath, relpath=''):
        self.path = srcpath
        self.relpath = relpath
        self.subdirs = []
        self.fileinfo = {}
        entryname = os.path.join(srcpath, 'CVS', 'Entries')
        try:
            f = open(entryname, 'r')
        except IOError:
            print >> sys.stderr, "note: cannot read", entryname
            return
        lines = f.readlines()
        f.close()
        entryname2 = os.path.join(srcpath, 'CVS', 'Entries.Log')
        try:
            f = open(entryname2, 'r')
        except IOError:
            pass
        else:
            for line in f.readlines():
                if line[:2] == 'A ':
                    lines.append(line[2:])
                elif line[:2] == 'R ':
                    lines.remove(line[2:])
            f.close()
        for line in lines:
            line = line.split('/')
            if len(line) >= 6:
                fname1 = line[1]
                if 'D' in line[0]:
                    self.subdirs.append(fname1)
                else:
                    self.fileinfo[fname1] = line
    def subdir(self, name):
        return Directory(os.path.join(self.path, name),
                         os.path.join(self.relpath, name))
    def alldirs(self):
        result = [self]
        for name in self.subdirs:
            result += self.subdir(name).alldirs()
        return result
    def unknownfiles(self):
        try:
            return [filename for filename in os.listdir(self.path)
                    if not self.fileinfo.has_key(filename) and
                       filename not in self.subdirs and
                       filename != 'CVS']
        except OSError:
            return []


if __name__ == '__main__':
    # print the full name of all the files
    root = Directory('.')
    for dir in root.alldirs():
        for name, info in dir.fileinfo.items():
            print os.path.join(dir.path, name)

##    # Example: print the full name of the files with revision 1.1.1.1
##    root = Directory('.')
##    for dir in root.alldirs():
##        for name, info in dir.fileinfo.items():
##            if info[2] == '1.1.1.1':
##                print os.path.join(dir.path, name)
