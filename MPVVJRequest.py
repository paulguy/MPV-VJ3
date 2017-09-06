# MPV-VJ3 Copyright 2017 paulguy <paulguy119@gmail.com>
#
# This file is part of MPV-VJ3.
#
# MPV-VJ3 is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MPV-VJ3 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MPV-VJ3.  If not, see <http://www.gnu.org/licenses/>.

import time

import JSONSocket
import MPVVJUtils

class MPVVJRequest:
    TPS = 20
    CONNECT_TIMEOUT = 30
    TIMEOUT_PERIOD = 45
    VERSION = 0

    def print(self, text='', end='\n'):
        if not self.quiet:
            print(text, end=end)

    def print_debug(self, text='', end='\n'):
        if not self.quiet and self.verbose:
            print(text, end=end)

    def __init__(self, quiet, verbose):
        if type(quiet) != bool:
            raise TypeError
        if type(verbose) != bool:
            raise TypeError
        self.quiet = quiet
        self.verbose = verbose
        self.socket = None
        self.connectTime = 0
        self.lastAct = 0
        self.formatStringParts = None
        self.fd = None

    def connectStart(self, host, port):
        if type(host) != str:
            raise TypeError
        if type(port) != int:
            raise TypeError
        if self.socket is not None:
            self.print("Already connected or connection in progress.")
            return False
        if port < 1 or port > 65535:
            raise ValueError("'port' must be between 1 and 65535.")
        self.print_debug("Connecting to " + host + " (" + str(port) + ")...")
        try:
            self.socket = JSONSocket.JSONTCPSocket(listening=False, host=host, port=port)
        except ConnectionError as e:
            raise e
        self.connectTime = time.monotonic()
        self.lastAct = time.monotonic()
        self.versionCheck()

    def connectCheck(self):
        if self.socket is not None:
            obj = None
            try:
                obj = self.socket.getJSONAsObj()
            except ConnectionRefusedError as e:
                self.disconnect()
                raise e
            except ConnectionError as e:
                self.disconnect()
                raise e

            if obj == None:
                if time.monotonic() - self.connectTime > self.CONNECT_TIMEOUT:
                    self.disconnect()
                    raise ConnectionError("Connection failed (Timed out).")
                else:
                    return True
            else:
                self.lastAct = time.monotonic()
                self.print_debug("server --> " + repr(obj))
                if 'event' in obj:
                    if obj['event'] == 'get-version':
                        if 'data' in obj:
                            if obj['data'] == self.VERSION:
                                return False
                            else:
                                self.disconnect()
                                raise ConnectionError("Version mismatch.  Server: " + obj['data'] + " Client: " + self.version)
                        else:
                            self.disconnect()
                            raise ConnectionError("'get-version' event with no 'data'.")
                    else:
                        self.disconnect()
                        raise ConnectionError("Expected 'get-version' event but got something else.")
                else:
                    self.disconnect()
                    raise ConnectionError("JSON statement with nothing to do.")
        else:
            raise ConnectionError("Socket isn't open.")

    def connect(self, host, port):
        self.connectStart(host, port)
        while self.connectCheck():
            time.sleep(1/self.TPS)

    def disconnect(self):
        if self.socket is not None:
            self.socket.close()

    def sendResponse(self, responseType, value, args=None):
        if args is None:
            args = {responseType: value}
        else:
            if type(args) != dict:
                raise TypeError
            args.update({responseType: value})

        if self.socket is not None:
            if self.socket.connected:
                self.print_debug("server <-- " + repr(args))
            else:
                self.print_debug("buffer <-- " + repr(args))
            try:
                self.socket.sendObjAsJSON(args)
                self.connectTime = time.monotonic()
            except ConnectionRefusedError:
                self.print("Connection refused.")
                self.disconnect()
            except BrokenPipeError:
                self.print("Broken pipe, connection dropped.")
                self.disconnect()
        else:
            self.print_debug("nobody <-- " + repr(args))

    def sendCommand(self, command, args=None):
        self.sendResponse('command', command, args)

    def versionCheck(self):
        self.sendCommand('get-version')

    def mpvOpts(self, opts):
        optsList = MPVVJUtils.parseKeyValues(opts)
        self.sendCommand('set-mpv-opts', {'opts': optsList})

    def run(self):
        self.sendCommand('run-mpv')

    def kill(self):
        self.sendCommand('terminate-mpv')

    def newPlaylist(self, name):
        self.sendCommand('new-playlists', {'playlists': [{'name': name}]})

    def deletePlaylist(self, name):
        self.sendCommand('delete-playlists', {'playlists': [name]})

    def selectPlaylist(self, playlist):
        self.sendCommand('select-playlist', {'playlist': playlist})

    def loop(self):
        self.sendCommand('toggle-looping')

    def shuffle(self):
        self.sendCommand('toggle-shuffle')

    def addItems(self, items):
        nameList = []
        for item in items:
            nameList.append({'name': item})
        self.sendCommand('add-items', {'items': nameList})

    def deleteItems(self, items):
        itemList = MPVVJUtils.parseRanges(items)
        self.sendCommand('delete-items', {'items': itemList})

    def setPlayed(self, items):
        itemList = MPVVJUtils.parseRanges(items)
        self.sendCommand('set-played', {'items': itemList, 'value': True})

    def setNotPlayed(self, items):
        itemList = MPVVJUtils.parseRanges(items)
        self.sendCommand('set-played', {'items': itemList, 'value': False})

    def track(self, track):
        self.sendCommand('track-relative', {'item': track})

    def trackNum(self, track):
        self.sendCommand('track-absolute', {'item': track})

    def loopFile(self):
        self.sendCommand('loop-file')

    def seek(self, seek):
        skip = parseTime(seek)
        self.sendCommand('mpv-command', {'mpv': ['add', 'time-pos', skip]})

    def time(self, time):
        skip = parseTime(time)
        self.sendCommand('mpv-command', {'mpv': ['set', 'time-pos', skip]})

    def vol(self, vol):
        self.sendCommand('mpv-command', {'mpv': ['add', 'ao-volume', vol]})

    def volume(self, vol):
        self.sendCommand('mpv-command', {'mpv': ['set', 'ao-volume', vol]})

    def mute(self):
        self.sendCommand('mpv-command', {'mpv': ['cycle', 'ao-mute']})

    def cue(self, playlist):
        self.sendCommand('cue-playlist', {'playlist': playlist})

    def play(self):
        self.sendCommand('play')

    def stop(self):
        self.sendCommand('stop')

    def toggle(self):
        self.sendCommand('mpv-command', {'mpv': ['cycle', 'pause']})

    def move(self, args):
        moveList = []
        playlist = None
        dest = 0

        try: # chop off the destination argument
            argsPeriod = args.rindex('.')
            dest = args[argsPeriod+1:]
            args = args[:argsPeriod]
        except ValueError:
            raise ValueError("No destination.")

        try: # try to see if there's a destination playlist argument
            destComma = dest.rindex(',')
            playlist = dest[:destComma]
            try:
                dest = int(dest[destComma+1:])
            except ValueError:
                raise ValueError("'pos' must be an integer.")
        except ValueError: # nope, just a number
            try:
                dest = int(dest)
            except ValueError:
                raise ValueError("'pos' must be an integer.")

        moveList = MPVVJUtils.parseRange(args)
        self.sendCommand('move-items', {'items': moveList, 'playlist': playlist, 'location': dest})

    def format(self, format):
        formatVars = []
        # find all replacements
        self.formatStringParts = []
        while len(format) > 0:
            try: # find start of next replacement
                percent1 = format.index('%')
                try: # find the end
                    percent2 = format.index('%', percent1 + 1)
                    if percent2 - percent1 > 1:
                        if len(self.formatStringParts) > 0 and len(self.formatStringParts[-1]) > 0 and self.formatStringParts[-1][-1] == '%':
                            self.formatStringParts[-1] += format[:percent1]
                        else:
                            self.formatStringParts.append(format[:percent1])
                        formatVars.append(format[percent1+1:percent2])
                    else: # literal %
                        if len(self.formatStringParts) > 0 and len(self.formatStringParts[-1]) > 0 and self.formatStringParts[-1][-1] == '%':
                            self.formatStringParts[-1] += '%'
                        else:
                            self.formatStringParts.append('%')
                    format = format[percent2+1:]
                except ValueError:
                    self.formatStringParts = None
                    raise ValueError("Unterminated replacement.")
            except ValueError as e: # none left
                if e.args[0] == "Unterminated replacement.":
                    raise e
                self.formatStringParts.append(format)
                format = ''

        self.sendCommand('get-properties', {'properties': formatVars})

    def list(self):
        self.sendCommand('list')

    def clear(self):
        self.sendCommand('clear')

    def killServer(self):
        self.sendCommand('kill')

    def status(self):
        self.format("""\
%artist% - %title%
[%status%] %position%/%playlistlength% %time%/%length% (%percentage%%%)
speed: %speed%x volume: %volume%%% muted: %muted% repeat: %repeat% single: %single%""")

    def checkForResponse(self):
        if self.socket is not None:
            obj = None
            try:
                obj = self.socket.getJSONAsObj()
            except ConnectionRefusedError as e:
                self.disconnect()
                raise e
            except ConnectionError as e:
                self.disconnect()
                raise e

            if obj != None:
                self.lastAct = time.monotonic()
                self.print_debug("server --> " + repr(obj))
                if 'event' in obj:
                    if obj['event'] == 'list':
                        playlists = []
                        playlist = None
                        currentPlaylist = None
                        playingPlaylist = None
                        selectedPlaylist = None
                        cued = None
                        playing = None
                        try:
                            playlists = obj['playlists']
                        except KeyError:
                            pass
                        try:
                            playlist = obj['playlist']
                        except KeyError:
                            pass
                        try:
                            currentPlaylist = obj['current-playlist']
                        except KeyError:
                            pass
                        try:
                            playingPlaylist = obj['playing-playlist']
                        except KeyError:
                            pass
                        try:
                            selectedPlaylist = obj['selected-playlist']
                        except KeyError:
                            pass
                        try:
                            cued = obj['cued']
                        except KeyError:
                            pass
                        try:
                            playing = obj['playing']
                        except KeyError:
                            pass
                        longest = 8
                        for i in playlists:
                            length = 0
                            try:
                                length = len(i['name'])
                            except KeyError:
                                i['name'] = "*** No name? ***"
                                length = len(i['name'])
                            longest = max(length, longest)
                        self.print("L S S C P Playlist")
                        self.print("- - - - - " + "{:-<{}}".format('', longest))
                        for i in enumerate(playlists):
                            try:
                                if i[1]['loop']:
                                    self.print("L ", end='')
                                else:
                                    self.print("  ", end='')
                            except KeyError:
                                self.print("  ", end='')
                            try:
                                if i[1]['shuffle']:
                                    self.print("S ", end='')
                                else:
                                    self.print("  ", end='')
                            except KeyError:
                                self.print("  ", end='')
                            if i[0] == selectedPlaylist:
                                self.print("* ", end='')
                            else:
                                self.print("  ", end='')
                            if i[0] == currentPlaylist:
                                self.print("* ", end='')
                            else:
                                self.print("  ", end='')
                            if i[0] == playingPlaylist:
                                self.print("> ", end='')
                            else:
                                self.print("  ", end='')
                            self.print(i[1]['name'])
                        if playlist != None:
                            digits = MPVVJUtils.numDigits(len(playlist))
                            longest = 4
                            for i in playlist:
                                length = 0
                                try:
                                    length = len(i['name'])
                                except KeyError:
                                    i['name'] = "*** No name? ***"
                                    length = len(i['name'])
                                longest = max(length, longest)
                            self.print()
                            self.print("P C P " + "{:>{}}".format('#', digits) + " Name")
                            self.print("- - - " + "{:-<{}} {:-<{}}".format('', digits, '', longest))
                            for i in enumerate(playlist):
                                try:
                                    if i[1]['played']:
                                        self.print("* ", end='')
                                    else:
                                        self.print("  ", end='')
                                except KeyError:
                                    self.print("  ", end='')
                                if i[0] == cued:
                                    self.print("* ", end='')
                                else:
                                    self.print("  ", end='')
                                if i[0] == playing:
                                    self.print("> ", end='')
                                else:
                                    self.print("  ", end='')
                                self.print("{:>{}} ".format(i[0], digits), end='')
                                try:
                                    self.print(i[1]['name'])
                                except KeyError:
                                    self.print("*** No name? ***")
                    elif obj['event'] == 'get-properties':
                        if 'properties' in obj:
                            if self.formatStringParts != None:
                                while len(self.formatStringParts) > 0 and len(obj['properties']) > 0:
                                    if len(self.formatStringParts) > 0:
                                        self.print(self.formatStringParts[0], end='')
                                        self.formatStringParts = self.formatStringParts[1:]
                                    if len(obj['properties']) > 0:
                                        self.print(str(obj['properties'][0]), end='')
                                        obj['properties'] = obj['properties'][1:]
                                self.print()
                                self.formatStringParts = None
                            else:
                                raise ValueError("Got properties back unexpectedly")
                        else:
                            raise KeyError("'get-properties' without 'properties'")
                    else:
                        self.print(obj['event'] + " OK")
                    return True
                if 'error' in obj:
                    if 'message' in obj:
                        self.print("Error: " + obj['message'])
                    else:
                        self.print("Unspecified error.")
                    return False
                else:
                    raise ValueError("JSON statement with nothing to do.")
        else:
            raise ConnectionError("Socket isn't open.")

    def waitForResponse(self):
        response = None
        while response == None:
            response = self.checkForResponse()
            time.sleep(1/self.TPS)

        return response
