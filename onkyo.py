import socket
import sys
import struct
import time

class ISCPError(Exception):
    pass

class OnkyoTCP(object):
    def __init__(self, ip="10.0.0.112", port=60128):
        self._ip = ip
        self._port = port
        self._socket = None
        self._rest = ""

    def connect(self):
        print (self._ip, self._port)
        #small timeout, receiver is supposd to answer in 50 ms but it may take several seconds
        self._socket = socket.create_connection((self._ip, self._port), timeout=2)

    def close(self):
        self._socket.close()

    def cmd(self, cmd):
        """
        send cmd to receiver with correct format
        """
        #the code is formated to follow as clearly as possible the specification
        headersize = struct.pack( ">i", 16)
        print "length cmd is ", len(cmd)
        datasize = struct.pack( ">i",  len(cmd)+1 ) 
        version = "\x01"
        reserved = "\x00\x00\x00"
        datastart = "!"
        unittype = "1"
        end = "\r"
        header = "ISCP" + headersize + datasize + version + reserved 
        print "length header ", len(header)
        self.line1 = header + datastart + unittype + cmd + end
        self.line = "ISCP\x00\x00\x00\x10\x00\x00\x00" + chr(len(cmd)+1) + "\x01\x00\x00\x00!1" + cmd + "\x0D"
        print len(self.line1), self.line1
        print len(self.line), self.line
        self._socket.sendall(self.line1)
        start = time.time()
        while True:
            ans = self._readStream()
            if ans == cmd:
                return ans
            if time.time() - start > 1:
                raise ISCPError("Receiver did not correctly anknowledge command,  sent: %s, received: %s" % (cmd, ans))
        return ans

    def _readStream(self):
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
        print "size of header is ", headersize 
        print "size of data is ", size 
        totalsize = headersize + size # contrarely to cmd we send, it seems the datasize includes end and start chars 
        print "total size should be ", totalsize 
        if len(msg) < totalsize:
            return "", msg
        msg = msg[:totalsize]
        rest = msg[totalsize:]
        data = msg[headersize:totalsize]
        cmd = data[2:-3] 
        return cmd, rest

    def z2power(self):
        self.cmd("ZPW01")

    def z2off(self):
        self.cmd("ZPW00")

def usage():
    pass

if __name__ == "__main__":
    if not len(sys.argv) > 2:
        usage()
    else:
        onkyo = OnkyoTCP()
        cmd = sys.argv[1]
        if cmd == "z2off":
            onkyo.z2off()
        elif cmd == "z2on":
            onkyo.z2power()
        else:
            usage()


