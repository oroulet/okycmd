"""
library to control an onkyo receiver over TCP/IP
it contains one client class called Onkyo
"""

import socket
import struct
import time
import sys
import os
import argparse


__author__ = "Olivier Roulet-Dubonnet"
__copyright__ = "Copyright 2011-2013, Olivier Roulet-Dubonnet"
__license__ = "GPLv3"


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
        self.lastmsg = ""  # debugging

    def _log(self, *args):
        if self._verbose:
            log = [str(i) for i in args]
            print("Onkyo: ".join(log))

    def connect(self):
        """
        connect to receiver
        """
        self._log("Connecting to: %s:%s" % (self._ip, self._port))
        # receiver is supposd to answer in 50 ms but in practice this may take several seconds
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
        if isinstance(cmd, str):
            cmd = cmd.encode()  # create byte string from text string otherwise hope it is a byte array
        self._log("Sending: ", cmd)
        headersize = struct.pack(">i", 16)
        datasize = struct.pack(">i", len(cmd) + 1)
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
            output.write(ans + "\n")
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
        self._log("received: ", cmd)
        return cmd

    def _parse(self, msg):
        """
        parse message from receiver
        The format seems slightly different from a packet we send
        en example answer is:
        'ISCP\x00\x00\x00\x10\x00\x00\x00\n\x01\x00\x00\x00!1PWR00\x1a\r\n'
        """
        self.lastmsg = msg  # debuging
        while msg and not msg.startswith(b"ISCP"):
            msg = msg[1:]
        if len(msg) < 12:
            return "", msg
        headersize = struct.unpack(">i", msg[4:8])[0]
        size = struct.unpack(">i", msg[8:12])[0]
        # print "size of header is ", headersize
        # print "size of data is ", size
        totalsize = headersize + size  # contrarely to cmd we send, it seems the datasize includes end and start chars
        # print "total size should be ", totalsize
        if len(msg) < totalsize:
            return "", msg
        msg = msg[:totalsize]
        rest = msg[totalsize:]
        data = msg[headersize:totalsize]
        cmd = data[2:-3]
        return cmd, rest


class Onkyo(object):
    """
    Class to send commands to an Onkyo receiver with an TCP interface
    The address of the receiver must be known, the port is standard but can be overridden if necessary
    Most methods are not documented since they have obvious names and simple logic
    """

    def __init__(self, host="10.0.0.112", port=60128, verbose=False):
        self._oky = OnkyoTCP(host, port, verbose=verbose)
        self._input2hex = {
            "VCR/DVR": b"00",
            "CBL/STAT": b"01",
            "GAME": b"02",
            "AUX": b"03",
            "AUX2": b"04",
            "PC": b"05",
            "BD/DVD": b"10",
            "TV/CD": b"23",
            "TUNER": b"24",
            "USB": b"29",
            "USB2": b"2A",
            "NET": b"2B",
            "DLNA": b"27",
            "NETRADIO": b"28",
            "PORT": b"40",
            "UP": b"UP",
            "DOWN": b"DOWN",
            "7F": b"OFF",
            "AUDISSEYSETUP": b"FF",
            "SOURCE": b"80"}
        # no bidirectional dict in python, so improvise
        self._hex2input = {v: k for k, v in self._input2hex.items()}

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
        source = self._oky.cmd("SLZQSTN")[3:]
        return self._hex2input[source]

    def z2setSource(self, source):
        ans = self._oky.cmd(b"SLZ" + self._input2hex[source])
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
        val = self._oky.cmd("ZTNQSTN")[3:]
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
        ans = self._oky.cmd(b"ZVL" + val)
        return int(ans[3:], 16)

    def z2getVolume(self):
        ans = self._oky.cmd("ZVLQSTN")
        if ans == b"ZVLN/A":  # FIXME: what should I do? return string or None
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
        ans = self._oky.cmd(b"MVL" + val)
        return int(ans[3:], 16)

    def _formatVolume(self, val):
        val = int(val)
        if val < 0:
            val = 0
        elif val > 80:
            val = 25  # do not break anything
        val = hex(val).upper()[2:].encode()
        if len(val) < 2:
            val = b"0" + val
        return val

    def getVolume(self):
        ans = self._oky.cmd("MVLQSTN")
        if ans == b"MVLN/A":
            return 0
        return int(ans[3:], 16)


def main():
    examples = """

Receiver IP address (and port) can be set using OKY_ADDRESS environment variable

cmd examples:
    oky --host 10.0.0.122 state ; print state for receiver at address 10.0.0.122
    oky source PC               ; set source to PC
    oky source                  ; print current source and available sources
    oky -z2 source SOURCE       ; set zone 2 source to the same as main zone
    oky source DLNA             ; set source DLNA(upnp) (this is a sub NET source)
    oky source NETRADIO         ; set source NET/RADIO (this is a sub NET source)
    oky on                      ; power on main zone
    oky -z2 off                 ; shut down zone 2
    oky -z2 +                   ; increase volume
    oky - 5                     ; decrease volume of 5 unit
    oky cmd IFVQSTN             ; send raw ISCP command to receiver

"""

    parser = argparse.ArgumentParser(description='Send commands to an Onkyo receiver', epilog=examples, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--verbose', '-v', action="store_true", help='be verbose')
    parser.add_argument('--host', default=None, help='IP address to use')
    parser.add_argument('--port', default=None, help='port number to use')
    parser.add_argument('--zone', "-z", default=1, type=int, choices=[1, 2], help='select zone')

    #parser.add_argument('zone', help='zone')
    #parser.add_argument('zone', nargs="?", choices=["z2", "main", ""], const="z2", default="main",  help='command to send')
    #parser.add_argument('cmd', choices=["source", "state"], help='command to send')
    parser.add_argument('cmd', help='command to send')
    parser.add_argument('val', nargs="?", default=None, help='command value')

    args = parser.parse_args()
    # print(args)

    if not args.cmd:  # this also catches --help case
        parser.print_help()
        sys.exit(1)
    else:
        host = None
        port = None
        if "OKY_ADDRESS" in os.environ:
            mystr = os.environ["OKY_ADDRESS"]
            if ":" in mystr:
                host, port = mystr.split(":")
            else:
                host = mystr
        if args.host:
            host = args.host
        if args.port:
            port = args.port
        else:
            port = 60128
        if not host:
            print("Error: Address IP not set")
            parser.print_help()
            sys.exit(1)

        oky = Onkyo(host=host, port=port, verbose=args.verbose)
        try:
            oky.connect()
        except socket.error as ex:
            print("Error connecting to device: ", ex)
            sys.exit(1)

        if args.cmd == "log":
            oky.log()
        elif args.cmd == "cmd":
            if args.val:
                print("Sending raw command to receiver", args.val)
                print(oky.sendCommand(args.val))
            else:
                print("cmd requires a value")
                parser.print_help()
        elif args.zone == 2:
            if args.cmd in ("off", "stop"):
                val = oky.z2off()
                print("Power: ", val)
            elif args.cmd in ("start", "on"):
                val = oky.z2power()
                print("Power: ", val)
            elif args.cmd.startswith("+"):
                v = args.cmd[1:]
                if not v:
                    v = "1"
                val = oky.z2volumeUp(v)
                print("Volume is: ", val)
            elif args.cmd.startswith("-"):
                v = args.cmd[1:]
                if not v:
                    v = "1"
                val = oky.z2volumeDown(v)
                print("Volume: ", val)
            elif args.cmd in ("vol", "volume"):
                if args.val:
                    val = oky.z2setVolume(args.val)
                else:
                    val = oky.z2getVolume()
                print("Volume: ", val)
            elif args.cmd == "source":
                if args.val:
                    source = oky.z2setSource(args.val)
                    print("Source: ", oky.z2getSource())
                else:
                    source = oky.z2getSource()
                    sources = oky.getSources()
                    print("Source: ", source)
                    print("Available sources: ", sources)
            elif args.cmd == "bass":
                if args.val in ("+", "up"):
                    bass, treble = oky.z2bassUp()
                elif args.val in ("-", "down"):
                    bass, treble = oky.z2bassDown()
                else:
                    bass, treble = oky.z2getTone()
                print("Bass: ", bass)
                print("Treble: ", treble)
            else:
                parser.print_help()
        elif args.cmd == "state":
            oky.printState()
        elif args.cmd in("stop", "off"):
            val = oky.off()
            print("Power: ", val)
        elif args.cmd in ("on", "start"):
            val = oky.power()
            print("Power: ", val)
        elif args.cmd == "source":
            if args.val:
                source = oky.setSource(args.val)
            else:
                source = oky.getSource()
            sources = oky.getSources()
            print("Source: ", source)
            print("Available sources: ", sources)
        elif args.cmd.startswith("+"):
            v = args.cmd[1:]
            if not v:
                v = "1"
            val = oky.volumeUp(v)
            print("Volume: ", val)
        elif args.cmd.startswith("-"):
            v = args.cmd[1:]
            if not v:
                v = "1"
            val = oky.volumeDown(v)
            print("Volume: ", val)
        elif args.cmd in ("vol", "volume"):
            if args.val:
                val = oky.setVolume(args.val)
            else:
                val = oky.getVolume()
            print("Volume: ", val)
        else:
            parser.print_help()

        oky.close()


if __name__ == "__main__":
    main()
