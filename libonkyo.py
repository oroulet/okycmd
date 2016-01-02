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
import logging


__author__ = "Olivier Roulet-Dubonnet"
__copyright__ = "Copyright 2011-2016, Olivier Roulet-Dubonnet"
__license__ = "GPLv3"


class ISCPError(Exception):
    pass


class OnkyoTCP(object):
    """
    control an onkyo receiver through its tcp interface
    """

    def __init__(self, host="10.0.0.112", port=60128):
        self._ip = host
        self._port = port
        self._socket = None
        self._rest = bytes()
        self.lastmsg = ""  # debugging
        self._logger = logging.getLogger("libonkyo")

    def connect(self):
        """
        connect to receiver
        """
        self._logger.info("Connecting to: %s:%s", self._ip, self._port)
        # receiver is supposd to answer in 50 ms but in practice this may take several seconds
        self._socket = socket.create_connection((self._ip, self._port), timeout=2)

    def close(self):
        """
        cleanup
        """
        self._logger.info("Closing socket")
        self._socket.close()

    def cmd(self, cmd):
        """
        send cmd to receiver with correct format
        the code is formated to follow as clearly as possible the specification, not to be efficient
        """
        if isinstance(cmd, str):
            cmd = cmd.encode()  # create byte string from text string otherwise hope it is a byte array
        self._logger.info("Sending: %s", cmd)
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
            ans = self._read_stream()
            if ans[:3] == cmd[:3]:
                return ans
            if time.time() - start > 1:
                raise ISCPError("Receiver did not correctly acknowledge command,  sent: %s, received: %s" % (cmd, ans))
        return ans

    def _read_stream(self, timeout=None):
        """
        read something from stream and return the first well formated packet
        put the rest on a queue which is read at next call of this method
        """
        if timeout:
            self._socket.settimeout(timeout)

        ans = self._socket.recv(1024)
        ans = self._rest + ans
        cmd, self._rest = self._parse(ans)
        self._logger.info("received: %s", cmd)
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

    def __init__(self, host="10.0.0.112", port=60128):
        self._oky = OnkyoTCP(host, port)
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

    def get_sources(self):
        return sorted(self._input2hex.keys())

    def connect(self):
        self._oky.connect()

    def send_command(self, cmd):
        return self._oky.cmd(cmd)

    def get_audio_information(self):
        return self._oky.cmd("IFAQSTN")[3:]

    def get_video_information(self):
        return self._oky.cmd("IFVQSTN")[3:]

    def print_state(self):
        power = self.get_power()
        source = self.get_source()
        vol = self.get_volume()
        video = self.get_video_information()
        audio = self.get_audio_information()
        print("""
        Main power: {}
        Main source: {} 
        Main volume (0-100): {} 
        Main audio: {} 
        Main video: {} 
        """.format(power, source, vol, audio, video))

        z2power = self.z2_get_power()
        z2_source = self.z2_get_source()
        z2_vol = self.z2_get_volume()
        print("""
        Zone2 power: {}
        Zone2 source: {}
        Zone2 volume (0-100): {}
        """ .format(z2power, z2_source, z2_vol))

    def close(self):
        self._oky.close()

    def get_power(self):
        return self._oky.cmd("PWRQSTN")[3:]

    def z2_get_source(self):
        source = self._oky.cmd("SLZQSTN")[3:]
        return self._hex2input[source]

    def z2_set_source(self, source):
        ans = self._oky.cmd(b"SLZ" + self._input2hex[source])
        return ans[3:]

    def z2_get_power(self):
        return self._oky.cmd("ZPWQSTN")[3:]

    def z2mute(self):
        return self._oky.cmd("ZMT00")[3:]

    def z2unmute(self):
        return self._oky.cmd("ZMT01")[3:]

    def z2_bass_up(self):
        val = self._oky.cmd("ZTNBUP")[3:]
        if val == b"N/A":
            return val, val
        else:
            return int(val[:2], 16), int(val[2:], 16)

    def z2_bass_down(self):
        val = self._oky.cmd("ZTNBDOWN")[3:]
        if val == b"N/A":
            return val, val
        else:
            return int(val[:2], 16), int(val[2:], 16)

    def z2_get_tone(self):
        val = self._oky.cmd("ZTNQSTN")[3:]
        if val == b"N/A":
            return val, val
        else:
            return int(val[:2], 16), int(val[2:], 16)

    def z2_treble_up(self):
        return self._oky.cmd("ZTNTUP")[3:]

    def z2_treble_down(self):
        return self._oky.cmd("ZTNTDOWN")[3:]

    def get_source(self):
        source = self._oky.cmd("SLIQSTN")[3:]
        return self._hex2input[source]

    def set_source(self, source):
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

    def z2_volume_up(self, val=None):
        if not val:
            ans = self._oky.cmd("ZVLUP")
            return int(ans[3:], 16)
        else:
            current = self.z2_get_volume()
            return self.z2_set_volume(current + int(val))

    def z2_volume_down(self, val=None):
        if not val:
            ans = self._oky.cmd("ZVLDOWN")
            return int(ans[3:], 16)
        else:
            current = self.z2_get_volume()
            return self.z2_set_volume(current - int(val))

    def z2_set_volume(self, val):
        """
        val must be between 0 and 80
        """
        val = self._format_volume(val)
        ans = self._oky.cmd(b"ZVL" + val)
        return int(ans[3:], 16)

    def z2_get_volume(self):
        ans = self._oky.cmd("ZVLQSTN")
        if ans == b"ZVLN/A":  # FIXME: what should I do? return string or None
            return 0
        return int(ans[3:], 16)

    def volume_up(self, val=None):
        if not val:
            ans = self._oky.cmd("MVLUP")
            return int(ans[3:], 16)
        else:
            current = self.get_volume()
            return self.set_volume(current + int(val))

    def volume_down(self, val=None):
        if not val:
            ans = self._oky.cmd("MVLDOWN")
            return int(ans[3:], 16)
        else:
            current = self.get_volume()
            return self.set_volume(current - int(val))

    def set_volume(self, val):
        """
        val must be between 0 and 80
        """
        val = self._format_volume(val)
        ans = self._oky.cmd(b"MVL" + val)
        return int(ans[3:], 16)

    def _format_volume(self, val):
        val = int(val)
        if val < 0:
            val = 0
        elif val > 80:
            val = 25  # do not break anything
        val = hex(val).upper()[2:].encode()
        if len(val) < 2:
            val = b"0" + val
        return val

    def get_volume(self):
        ans = self._oky.cmd("MVLQSTN")
        if ans == b"MVLN/A":
            return 0
        return int(ans[3:], 16)


def make_parser():
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

    parser.add_argument('cmd', help='command to send')
    parser.add_argument('val', nargs="?", default=None, help='command value')

    return parser


def parse_args(parser):
    args = parser.parse_args()
    # print(args)

    loglevel = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=loglevel)

    if not args.cmd:  # this also catches --help case
        parser.print_help()
        sys.exit(1)

    return args


def get_host_and_port(args, parser):
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

    return host, port


def main():
    parser = make_parser()
    args = parse_args(parser)
    host, port = get_host_and_port(args, parser)

    oky = Onkyo(host=host, port=port)
    try:
        oky.connect()
    except socket.error as ex:
        print("Error connecting to device: ", ex)
        sys.exit(1)

    send_command(args, parser, oky)

    oky.close()


def send_z2_command(args, parser, oky):
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
        val = oky.z2_volume_up(v)
        print("Volume is: ", val)
    elif args.cmd.startswith("-"):
        v = args.cmd[1:]
        if not v:
            v = "1"
        val = oky.z2_volume_down(v)
        print("Volume: ", val)
    elif args.cmd in ("vol", "volume"):
        if args.val:
            val = oky.z2_set_volume(args.val)
        else:
            val = oky.z2_get_volume()
        print("Volume: ", val)
    elif args.cmd == "source":
        if args.val:
            source = oky.z2_set_source(args.val)
            print("Source: ", oky.z2_get_source())
        else:
            source = oky.z2_get_source()
            sources = oky.get_sources()
            print("Source: ", source)
            print("Available sources: ", sources)
    elif args.cmd == "bass":
        if args.val in ("+", "up"):
            bass, treble = oky.z2_bass_up()
        elif args.val in ("-", "down"):
            bass, treble = oky.z2_bass_down()
        else:
            bass, treble = oky.z2_get_tone()
        print("Bass: ", bass)
        print("Treble: ", treble)
    else:
        parser.print_help()


def send_command(args, parser, oky):
    if args.cmd == "cmd":
        if args.val:
            print("Sending raw command to receiver", args.val)
            print(oky.send_command(args.val))
        else:
            print("cmd requires a value")
            parser.print_help()
    elif args.zone == 2:
        send_z2_command(args, parser, oky)
    elif args.cmd == "state":
        oky.print_state()
    elif args.cmd in("stop", "off"):
        val = oky.off()
        print("Power: ", val)
    elif args.cmd in ("on", "start"):
        val = oky.power()
        print("Power: ", val)
    elif args.cmd == "source":
        if args.val:
            source = oky.set_source(args.val)
        else:
            source = oky.get_source()
        sources = oky.get_sources()
        print("Source: ", source)
        print("Available sources: ", sources)
    elif args.cmd.startswith("+"):
        v = args.cmd[1:]
        if not v:
            v = "1"
        val = oky.volume_up(v)
        print("Volume: ", val)
    elif args.cmd.startswith("-"):
        v = args.cmd[1:]
        if not v:
            v = "1"
        val = oky.volume_down(v)
        print("Volume: ", val)
    elif args.cmd in ("vol", "volume"):
        if args.val:
            val = oky.set_volume(args.val)
        else:
            val = oky.get_volume()
        print("Volume: ", val)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
