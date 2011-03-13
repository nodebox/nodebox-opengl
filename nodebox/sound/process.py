#=== SOUND ===========================================================================================
# Convenience classes and functions for audio manipulation.
# Authors: Frederik De Bleser, Lieven Menschaert, Tom De Smedt.
# License: BSD (see LICENSE.txt for details).
# Copyright (c) 2008 City In A Bottle (cityinabottle.org)
# http://cityinabottle.org/nodebox

import osc
import sys
import os
import subprocess
import StringIO
import signal
import time
import socket as _socket

def _find(match=lambda item: False, list=[]):
    """ Returns the first item in the list for which match(item)=True, or None.
    """
    for item in list:
        if match(item): return item

#=====================================================================================================

#--- PROCESS -----------------------------------------------------------------------------------------

# True when running on Windows.
WINDOWS = sys.platform.startswith('win')

if not WINDOWS:
    import select
    import fcntl
    def read_non_blocking(stream, bytes=1024, timeout=0):
        # Reads a number of bytes from the given stream, 
        # without deadlocking when no more data is available (returns None instead).
        fcntl.fcntl(stream, fcntl.F_SETFL, fcntl.fcntl(stream, fcntl.F_GETFL) | os.O_NONBLOCK)
        if not select.select([stream], [], [], 0)[0]:
            return None
        return stream.read(bytes)
    
if WINDOWS:
    import ctypes; from ctypes.wintypes import DWORD
    import msvcrt
    def read_non_blocking(stream, bytes=1024):
        # Reads a number of bytes from the given stream, 
        # without deadlocking when no more data is available (returns None instead).
        p = msvcrt.get_osfhandle(stream.fileno())
        s = ctypes.create_string_buffer(1)
        b = ctypes.windll.kernel32.PeekNamedPipe(p, s, 1, None, None, None)
        if s.value:
            c_read = DWORD()
            s = ctypes.create_string_buffer(bytes+1)
            b = ctypes.windll.kernel32.ReadFile(p, s, bytes+1, ctypes.byref(c_read), None)
            s[c_read.value] = '\0'
            return s.value.decode()

class Process(object):
    
    def __init__(self, program, options={}, start=True):
        """ Runs the given program (i.e. executable file path) as a background process
            with the given command-line options.
        """
        self.program  = program
        self.options  = options
        self._process = None
        if start:
            self.start()
        
    @property
    def started(self):
        return self._process is not None
    
    @property
    def id(self):
        return self._process \
           and self._process.pid or None
        
    pid = id
    
    @property
    def output(self, bytes=1024):
        # Yields a number of bytes of output, or None if the process is idle.
        if self._process is not None:
            return read_non_blocking(self._process.stdout, bytes)
    
    def start(self):
        """ Starts the program with the given command-line options.
            The output can be read from Process.output.
        """
        o = [self.program]; [o.extend((k,v)) for k,v in self.options.items()]
        o = [str(x) for x in o if x is not None]
        self._process = subprocess.Popen(o,
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT
        )
    
    def stop(self):
        """ Attempts to stop the process.
            Returns True when the process is stopped, False otherwise.
        """
        if not self._process:
            # The process has not been started.
            return True
        if hasattr(self._process, 'kill'):
            # Popen.kill() works in Python 2.6+ on all platforms.
            self._process.kill()
            self._process = None
            return True
        if self._process.pid is not None and not WINDOWS:
            # os.kill() works in Python 2.4+ on Unix and Mac OS X.
            os.kill(self._process.pid, signal.SIGTERM)
            time.sleep(0.1)
            self._process = None
            return True
        if self._process.pid is not None and WINDOWS:
            # Use ctypes on Windows platforms.
            import ctypes
            p = ctypes.windll.kernel32.OpenProcess(1, False, self._process.pid)
            ctypes.windll.kernel32.TerminateProcess(p, -1)
            ctypes.windll.kernel32.CloseHandle(p)
            time.sleep(0.1)
            self._process = None
            return True
        return False

#=====================================================================================================

#--- SOCKET ------------------------------------------------------------------------------------------

class Socket(_socket.socket):
    
    def __init__(self, host, port):
        """ Creates a socket connection to the given host (IP address) and port.
            Socket.close() will close the connection when Socket.connections is 0
        """
        _socket.socket.__init__(self, _socket.AF_INET, _socket.SOCK_DGRAM)
        self.bind((host, port))
        self.setblocking(0)
        self.connections = 0
    
    def close(self):
        if self.connections <= 0:
            _socket.socket.close(self)

_sockets = {}
def socket(host, port):
    """ Returns the socket connection to the given host and port, creating it when none exists.
    """
    return _sockets.setdefault("%s:%s" % (host, port), Socket(host, port))

#--- PUREDATA ----------------------------------------------------------------------------------------

# Pd application default paths:
# /usr/local/bin/pd
# /Applications/Pd-extended.app/Contents/Resources/bin/pd
# C:\Program Files\pd\bin\pd.exe
PD_UNIX1   = "pdextended"
PD_UNIX2   = "pd"
PD_MACOSX  = "Pd-extended.app/Contents/Resources/bin/pd"
PD_WINDOWS = "pd\\bin\\pd.exe"
DEFAULT    = "default"

# Default server.
LOCALHOST  = "127.0.0.1"

# Default ports.
# PD.get() receives on port 44000, the Pd patch broadcasts on port 44000.
# PD.send() broadcasts on port 44001, the Pd patch receives on port 44001.
IN  = 44000
OUT = 44001

class PDError(Exception):
    pass

class PD(object):   
    
    def __init__(self, patch=None, buffer=128, options={}, start=False, path=DEFAULT):
        """ Creates a network connection with PureData.
            When a patch (.pd file) is given and start=True, loads PD with the patch in the background.
            Otherwise, communication can be established with whatever patch is active in a running PD.
            The PD.send() method sends data to the patch running at a given host and port.
            The path defines the location of the PD executable.
            A number of default locations are searched as well:
            - the current folder,
            - /usr/bin/pdextended (Unix, preferred),
            - /usr/local/bin/pd (Unix),
            - /Applications/Pd-extended.app/Contents/Resources/bin/pd (Mac OS X),
            - C:\Program Files\pd\bin\pd.exe (Windows).
            Command-line options can be given as a dictionary, e.g.
            PD(options={'-alsa': None})
        """
        path = path != DEFAULT and path or ""
        path = _find(lambda x: os.path.exists(x), [
            path,
            os.path.join(path, PD_UNIX1),
            os.path.join(path, PD_UNIX2),
            os.path.join(path, PD_MACOSX),
            os.path.join(path, PD_WINDOWS),
                   "usr/bin/" + PD_UNIX1,
             "usr/local/bin/" + PD_UNIX1,
                   "usr/bin/" + PD_UNIX2,
             "usr/local/bin/" + PD_UNIX2,
             "/Applications/" + PD_MACOSX,
        "C:\\Program Files\\" + PD_WINDOWS
        ])
        self._path     = path          # PD executable location.
        self._process  = None          # PD executable running in background.
        self._callback = {}            # [PDCallback, data] items indexed by path + host + port.
        self._options  = dict(options) # For PD-Extended 0.41- on Mac OS X, only works with -nogui.
        self._options.setdefault("-nogui", None)
        self._options.setdefault("-audiobuf", buffer)
        self._options.setdefault("-open", patch)
        if start:
            self.start()
        osc.init()
            
    @property    
    def patch(self):
        return self._options.get("-open")
    @property
    def buffer(self):
        return self._options.get("-audiobuf")
    
    def start(self):
        """ Starts PD as a background process and loads PD.patch.
            If PD is already running another patch, restarts the application.
        """
        if self.patch is None \
        or not os.path.exists(self.patch):
            raise PDError, "no PD patch file at '%s'" % self.patch
        if not os.path.exists(self._path):
            raise PDError, "no PD application at '%s'" % self._path
        if not self._process:
            self._process = Process(program=self._path, options=self._options)
    
    def stop(self):
        for callback in self._callback.values():
            callback.stop()
        return self._process \
           and self._process.stop()
            
    def send(self, data, path, host=LOCALHOST, port=OUT):
        """ Sends the given list of data over OSC to PD.
            The path specifies the address where PD receives the data e.g. "/creature/perch".
        """
        osc.sendMsg(path, data, host, port)
        
    def get(self, path, host=LOCALHOST, port=IN):
        """ Returns the data sent from the given path in PD.
        """
        id = "%s%s%s" % (path, host, port)
        if not id in self._callback:
            self._callback[id] = PDCallback(path, host, port)
        return self._callback[id].data
        
    def __del__(self):
        try: self.stop()
        except:
            pass
            
    @property
    def output(self):
        return self._process.output

class PDCallback:
    
    def __init__(self, path, host=LOCALHOST, port=44001):
        """ Creates a listener for data broadcast from Pd.
            PDCallback.__call__() is called from PD.get().
        """
        osc.bind(self, path)
        self._path   = path
        self._data   = []
        self._socket = socket(host, port)
        self._socket.connections += 1
        
    def __call__(self, *data):
        # First two arguments in the list are the path and typetags string.
        self._data = data[0][2:] if data != "nodata" else []
    
    @property
    def data(self):
        osc.getOSC(self._socket)
        return self._data
        
    def stop(self):
        self._socket.connections -= 1
        self._socket.close()
        self._socket = None