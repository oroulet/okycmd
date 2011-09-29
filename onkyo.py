import socket
import struct
import time

class ISCPError(Exception):
    pass

class OnkyoTCP(object):
    """
    control an onkyo receiver through its tcp interface
    """
    def __init__(self, ip="10.0.0.112", port=60128):
        self._ip = ip
        self._port = port
        self._socket = None
        self._rest = ""

    def connect(self):
        """
        connect to receiver
        """
        print "Connecting to: ", (self._ip, self._port)
        #small timeout, receiver is supposd to answer in 50 ms but it may take several seconds
        self._socket = socket.create_connection((self._ip, self._port), timeout=2)

    def close(self):
        """
        cleanup
        """
        self._socket.close()

    def cmd(self, cmd):
        """
        send cmd to receiver with correct format
        """
        print "Sending: ", cmd
        #the code is formated to follow as clearly as possible the specification
        headersize = struct.pack( ">i", 16)
        #print "length cmd is ", len(cmd)
        datasize = struct.pack( ">i",  len(cmd)+1 ) 
        version = "\x01"
        reserved = "\x00\x00\x00"
        datastart = "!"
        unittype = "1"
        end = "\r"
        header = "ISCP" + headersize + datasize + version + reserved 
        #print "length header ", len(header)
        line = header + datastart + unittype + cmd + end
        #print len(line), line
        self._socket.sendall(line)
        start = time.time()
        while True:
            ans = self._readStream()
            if ans[:3] == cmd[:3]:
                return ans
            if time.time() - start > 1:
                raise ISCPError("Receiver did not correctly anknowledge command,  sent: %s, received: %s" % (cmd, ans))
        return ans

    def _readStream(self):
        """
        read something from stream and return the first well formated packet
        put the rest on a queue which is read at next call of this method
        """
        ans = self._socket.recv(1024)
        ans = self._rest + ans
        cmd, self._rest = self._parse(ans)
        print "received: ", cmd
        return cmd

    def _parse(self, msg):
        """
        parse message from receiver
        The format seems slightly different from a packet we send
        en example answer is:
        'ISCP\x00\x00\x00\x10\x00\x00\x00\n\x01\x00\x00\x00!1PWR00\x1a\r\n'
        """
        self.msg = msg # debuging
        while msg and not msg.startswith("ISCP"):
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
    def __init__(self, ip="10.0.0.112", port=60128):
        self._oky = OnkyoTCP(ip, port)
        self._input2hex = {
                "VCR/DVR":"00",
                "CBL/STAT":"01", 
                "GAME":"02",
                "AUX":"03",
                "AUX2":"04",
                "PC":"05",
                "BD/DVD":"10",
                "TV/CD":"23",
                "TUNER":"24",
                "PORT":"40",
                "USB":"29",
                "USB2":"2A",
                "NET":"2B",
                "UP":"UP",
                "DOWN":"DOWN",
                "7F":"OFF",
                "AUDISSEYSETUP":"FF",
                "SOURCE":"80"}
        #no bidirectional dict in python, so improvise
        self._hex2input = {}
        for k, v in self._input2hex.items():
            self._hex2input[v] = k

    def connect(self):
        self._oky.connect()

    def printState(self):
        power = self.getPower()
        source = self.getSource()
        vol = self.getVolume()
        print """
        Main power: %s
        Main source: %s
        Main volume (0-100): %s

        """ % (power, source, vol)

        z2power = self.z2getPower()
        z2source = self.z2getSource()
        z2vol = self.z2getVolume()
        print """
        Zone2 power: %s
        Zone2 source: %s
        Zone2 volume (0-100): %s
        """ % (z2power, z2source, z2vol)

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
        if val == "N/A":
            return val, val
        else:
            return int(val[:2], 16), int(val[2:], 16)

    def z2bassDown(self):
        val = self._oky.cmd("ZTNBDOWN")[3:]
        if val == "N/A":
            return val, val
        else:
            return int(val[:2], 16), int(val[2:], 16)

    def z2getTone(self):
        val =  self._oky.cmd("ZTNQSTN")[3:]
        if val == "N/A":
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
        ans = self._oky.cmd("SLI" + self._input2hex[source])
        return ans[3:]

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

    def z2volumeUp(self):
        ans = self._oky.cmd("ZVLUP")
        return int(ans[3:], 16)

    def z2volumeDown(self):
        ans = self._oky.cmd("ZVLDOWN")
        return int(ans[3:], 16)

    def z2setVolume(self, val):
        """
        val must be between 0 and 80
        """
        val = self._formatVolume(val)
        ans = self._oky.cmd("ZVL" + val)
        return int(ans[3:], 16)

    def z2getVolume(self):
        ans = self._oky.cmd("ZVLQSTN")
        return int(ans[3:], 16)

    def volumeUp(self):
        val = self._oky.cmd("MVLUP")[3:]
        return int(val, 16)

    def volumeDown(self):
        val = self._oky.cmd("MVLDOWN")[3:]
        return int(val, 16)

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
        val = hex(val).upper()[2:]
        print val
        if len(val) < 2:
            print val
            val = "0" + val  
        return val

    def getVolume(self):
        ans = self._oky.cmd("MVLQSTN")
        return int(ans[3:], 16)
        


if __name__ == "__main__":
    oky = Onkyo()
    oky.connect()


