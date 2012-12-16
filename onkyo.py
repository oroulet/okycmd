"""
library to control an onkyo receiver over TCP/IP
it contains one client class called Onkyo
"""
import socket
import struct
import time
import sys


__author__ = "Olivier Roulet-Dubonnet"
__copyright__ = "Copyright 2011-2012, Olivier Roulet-Dubonnet"
__credits__ = ["Olivier Roulet-Dubonnet"]
__license__ = "GPLv3"
__version__ = "0.3"
__status__ = "Development"



class ISCPError(Exception):
    pass

class OnkyoTCP(object):
    """
    control an onkyo receiver through its tcp interface
    """
    def __init__(self, host="10.0.0.112", port=60128, verbose=False):
        self._ip = host
        self._port = port
        self._socket = None
        self._rest = bytes()
        self._verbose = verbose
        self.lastmsg = "" # debugging

    def _log(self, *args):
        if self._verbose:
            log = [str(i) for i in args]
            print("Onkyo: ".join(log))

    def connect(self):
        """
        connect to receiver
        """
        self._log( "Connecting to: %s:%s" % (self._ip, self._port))
        #receiver is supposd to answer in 50 ms but in practice this may take several seconds
        self._socket = socket.create_connection((self._ip, self._port), timeout=2)

    def close(self):
        """
        cleanup
        """
        self._log("Closing socket")
        self._socket.close()

    def cmd(self, cmd):
        """
        send cmd to receiver with correct format
        the code is formated to follow as clearly as possible the specification, not to be efficient
        """
        if type(cmd) == str:
            cmd = cmd.encode() # create byte string from text string otherwise hope it is a byte array
        self._log( "Sending: ", cmd)
        headersize = struct.pack( ">i", 16)
        datasize = struct.pack( ">i",  len(cmd)+1 ) 
        version = b"\x01"
        reserved = b"\x00\x00\x00"
        datastart = b"!"
        unittype = b"1"
        end = b"\r"
        header = b"ISCP" + headersize + datasize + version + reserved 
        line = header + datastart + unittype + cmd + end
        self._socket.sendall(line)
        start = time.time()
        while True:
            ans = self._readStream()
            if ans[:3] == cmd[:3]:
                return ans
            if time.time() - start > 1:
                raise ISCPError("Receiver did not correctly acknowledge command,  sent: %s, received: %s" % (cmd, ans))
        return ans

    def log(self, output=sys.stdout):
        while True:
            ans = self._readStream(timeout=36000)
            output.write(ans+"\n")
            output.flush()

    def _readStream(self, timeout=None):
        """
        read something from stream and return the first well formated packet
        put the rest on a queue which is read at next call of this method
        """
        if timeout:
            self._socket.settimeout(timeout)

        ans = self._socket.recv(1024)
        ans = self._rest + ans
        cmd, self._rest = self._parse(ans)
        self._log( "received: ", cmd )
        return cmd

    def _parse(self, msg):
        """
        parse message from receiver
        The format seems slightly different from a packet we send
        en example answer is:
        'ISCP\x00\x00\x00\x10\x00\x00\x00\n\x01\x00\x00\x00!1PWR00\x1a\r\n'
        """
        self.lastmsg = msg # debuging
        while msg and not msg.startswith(b"ISCP"):
            msg = msg[1:]
        if len(msg) < 12:
            return "", msg
        headersize = struct.unpack(">i", msg[4:8])[0]
        size = struct.unpack(">i", msg[8:12])[0]
        #print "size of header is ", headersize 
        #print "size of data is ", size 
        totalsize = headersize + size # contrarely to cmd we send, it seems the datasize includes end and start chars 
        #print "total size should be ", totalsize 
        if len(msg) < totalsize:
            return "", msg
        msg = msg[:totalsize]
        rest = msg[totalsize:]
        data = msg[headersize:totalsize]
        cmd = data[2:-3] 
        return cmd, rest



class Onkyo(object):
    """
    class to send commands to a receiver.
    """
    def __init__(self, host="10.0.0.112", port=60128, verbose=False):
        self._oky = OnkyoTCP(host, port, verbose=verbose)
        self._input2hex = {
                "VCR/DVR":b"00",
                "CBL/STAT":b"01", 
                "GAME":b"02",
                "AUX":b"03",
                "AUX2":b"04",
                "PC":b"05",
                "BD/DVD":b"10",
                "TV/CD":b"23",
                "TUNER":b"24",
                "USB":b"29",
                "USB2":b"2A",
                "NET":b"2B",
                "DLNA":b"27",
                "NETRADIO":b"28",
                "PORT":b"40",
                "UP":b"UP",
                "DOWN":b"DOWN",
                "7F":b"OFF",
                "AUDISSEYSETUP":b"FF",
                "SOURCE":b"80"}
        #no bidirectional dict in python, so improvise
        self._hex2input = {}
        for k, v in self._input2hex.items():
            self._hex2input[v] = k

    def getSources(self):
        return sorted(self._input2hex.keys())

    def log(self):
        self._oky.log()

    def connect(self):
        self._oky.connect()

    def sendCommand(self, cmd):
        return self._oky.cmd(cmd)

    def getAudioInformation(self):
        return self._oky.cmd("IFAQSTN")[3:]

    def getVideoInformation(self):
        return self._oky.cmd("IFVQSTN")[3:]

    def printState(self):
        power = self.getPower()
        source = self.getSource()
        vol = self.getVolume()
        video = self.getVideoInformation()
        audio = self.getAudioInformation()
        print("""
        Main power: %s
        Main source: %s
        Main volume (0-100): %s
        Main audio: %s
        Main video: %s
        """ % (power, source, vol, audio, video)
        )

        z2power = self.z2getPower()
        z2source = self.z2getSource()
        z2vol = self.z2getVolume()
        print("""
        Zone2 power: %s
        Zone2 source: %s
        Zone2 volume (0-100): %s
        """ % (z2power, z2source, z2vol)
        )

    def close(self):
        self._oky.close()

    def getPower(self):
        return self._oky.cmd("PWRQSTN")[3:]

    def z2getSource(self):
        source =  self._oky.cmd("SLZQSTN")[3:]
        return self._hex2input[source]

    def z2setSource(self, source):
        ans = self._oky.cmd("SLZ" + self._input2hex[source])
        return ans[3:]

    def z2getPower(self):
        return self._oky.cmd("ZPWQSTN")[3:]

    def z2mute(self):
        return self._oky.cmd("ZMT00")[3:]

    def z2unmute(self):
        return self._oky.cmd("ZMT01")[3:]

    def z2bassUp(self):
        val = self._oky.cmd("ZTNBUP")[3:]
        if val == b"N/A":
            return val, val
        else:
            return int(val[:2], 16), int(val[2:], 16)

    def z2bassDown(self):
        val = self._oky.cmd("ZTNBDOWN")[3:]
        if val == b"N/A":
            return val, val
        else:
            return int(val[:2], 16), int(val[2:], 16)

    def z2getTone(self):
        val =  self._oky.cmd("ZTNQSTN")[3:]
        if val == b"N/A":
            return val, val
        else:
            return int(val[:2], 16), int(val[2:], 16)

    def z2trebleUp(self):
        return self._oky.cmd("ZTNTUP")[3:]

    def z2trebleDown(self):
        return self._oky.cmd("ZTNTDOWN")[3:]

    def getSource(self):
        source = self._oky.cmd("SLIQSTN")[3:]
        return self._hex2input[source]

    def setSource(self, source):
        ans = self._oky.cmd(b"SLI" + self._input2hex[source])
        return self._hex2input[ans[3:]]

    def power(self):
        ans = self._oky.cmd("PWR01")
        return ans[3:]

    def off(self):
        ans = self._oky.cmd("PWR00")
        return ans[3:]

    def z2power(self):
        ans = self._oky.cmd("ZPW01")
        return ans[3:]

    def z2off(self):
        ans = self._oky.cmd("ZPW00")
        return ans[3:]

    def z2volumeUp(self, val=None):
        if not val:
            ans = self._oky.cmd("ZVLUP")
            return int(ans[3:], 16)
        else:
            current = self.z2getVolume()
            return self.z2setVolume(current + int(val))


    def z2volumeDown(self, val=None):
        if not val:
            ans = self._oky.cmd("ZVLDOWN")
            return int(ans[3:], 16)
        else:
            current = self.z2getVolume()
            return self.z2setVolume(current - int(val))

    def z2setVolume(self, val):
        """
        val must be between 0 and 80
        """
        val = self._formatVolume(val)
        ans = self._oky.cmd("ZVL" + val)
        return int(ans[3:], 16)

    def z2getVolume(self):
        ans = self._oky.cmd("ZVLQSTN")
        if ans == b"ZVLN/A":#FIXME: what should I do? return string or Noen
            return 0 
        return int(ans[3:], 16)

    def volumeUp(self, val=None):
        if not val:
            ans = self._oky.cmd("MVLUP")
            return int(ans[3:], 16)
        else:
            current = self.getVolume()
            return self.setVolume(current + int(val))

    def volumeDown(self, val=None):
        if not val:
            ans = self._oky.cmd("MVLDOWN")
            return int(ans[3:], 16)
        else:
            current = self.getVolume()
            return self.setVolume(current - int(val))

    def setVolume(self, val):
        """
        val must be between 0 and 80
        """
        val = self._formatVolume(val)
        ans = self._oky.cmd("MVL" + val)
        return int(ans[3:], 16)

    def _formatVolume(self, val):
        val = int(val)
        if val < 0:
            val = 0
        elif val > 80:
            val = 25 # do not break anything
        val = hex(val).upper()[2:].encode()
        if len(val) < 2:
            val = b"0" + val  
        return val

    def getVolume(self):
        ans = self._oky.cmd("MVLQSTN")
        if ans == b"MVLN/A":
            return 0
        return int(ans[3:], 16)
        


if __name__ == "__main__":
    oky = Onkyo()
    oky.connect()


