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
import json
import random
import signal
import os
import os.path
import argparse

import MPVVJState
import JSONSocket
import MPV
import MPVVJUtils

# TODO
# bugs and crashes

TPS = 20
DEFAULT_MPV = "/usr/bin/mpv"
DEFAULT_SOCKET = "/tmp/mpvsocket"
DEFAULT_PORT = 12345
DEFAULT_BIND_ADDRESS = "127.0.0.1"


def hupHandler(signum, frame):
    print("SIGHUP received.")
    try:
        server
    except NameError:
        return

    if server.socket is not None:
        server.reconnectSocket()
        print("Listening socket forcibly closed and reopened")


class PlaylistStop(BaseException):
    pass


class MPVVJServer():
    RETRIES = 3
    TIMEOUT = 45
    VERSION = 0

    REPLACEMENT_NONE = 'N/A'

    MPV_PROPERTY_REQUEST = {
        'title':        ('get_property',        'metadata/by-key/title',        0),
        'artist':       ('get_property',        'metadata/by-key/artist',       1),
        'album':        ('get_property',        'metadata/by-key/album',        2),
        'albumartist':  ('get_property',        'metadata/by-key/album_artist', 3),
        'genre':        ('get_property',        'metadata/by-key/genre',        4),
        'year':         ('get_property',        'metadata/by-key/date',         5),
        'status':       ('get_property',        'pause',                        6),
        'time':         ('get_property_string', 'time-pos',                     7),
        'precisetime':  ('get_property_string', 'time-pos',                     8),
        'length':       ('get_property',        'duration',                     9),
        'percentage':   ('get_property',        'percent-pos',                  10),
        'speed':        ('get_property_string', 'speed',                        11),
        'volume':       ('get_property_string', 'volume',                       12),
        'muted':        ('get_property',        'mute',                         13),
        'frame':        ('get_property',        'estimated-frame-number',       14)
    }

    MPV_COMMAND_REQUEST_ID = 15

    MPV_PROPERTY_SET = {
        0: ('title',        None),
        1: ('artist',       None),
        2: ('album',        None),
        3: ('albumartist',  None),
        4: ('genre',        None),
        5: ('year',         None),
        6: ('status',       MPVVJUtils.statusStr),
        7: ('time',         MPVVJUtils.toTime),
        8: ('precisetime',  MPVVJUtils.toPreciseTime),
        9: ('length',       MPVVJUtils.toTime),
        10: ('percentage',  MPVVJUtils.roundTenth),
        11: ('speed',       MPVVJUtils.roundTenth),
        12: ('volume',      MPVVJUtils.roundTenth),
        13: ('muted',       MPVVJUtils.boolYesNo),
        14: ('frame',       None)
    }

    def print(self, text):
        if not self.quiet:
            print(text)

    def print_debug(self, text):
        if not self.quiet and self.verbose:
            print(text)

    def __init__(self, mpvPath, socketPath, bindAddress, port, quiet, verbose):
        self.mpvPath = mpvPath
        self.socketPath = socketPath
        self.bindAddress = bindAddress
        self.port = port
        self.quiet = quiet
        self.verbose = verbose
        self.mpvopts = []
        self.state = MPVVJState.MPVVJState()
        self.socket = None
        self.reconnectSocket()
        self.mpv = None
        self.connected = False
        self.playing = False
        self.path = os.getcwd()
        signal.signal(signal.SIGHUP, hupHandler)

        self.lastAct = None
        self.lastConnectionAttempt = 0
        
        self.neededProperties = None
        self.waitForCommand = False

    def disconnectSocket(self):
        if self.socket is not None:
            self.socket.close()

    def reconnectSocket(self):
        self.disconnectSocket()
        self.print("Binding to " + self.bindAddress + " (" + str(self.port) + ").")
        self.socket = JSONSocket.JSONTCPSocket(listening=True, host=self.bindAddress,
                                               port=self.port)
        self.lastAct = None

    def terminateMpv(self):
        if self.mpv is not None:
            self.mpv.terminate()
            self.mpv = None
            self.connected = False
            self.playing = False

    def cleanUp(self):
        self.terminateMpv()
        self.disconnectSocket()

    def sendResponse(self, responseType, value, args=None):
        if args is None:
            args = {responseType: value}
        else:
            if type(args) != dict:
                raise TypeError
            args.update({responseType: value})

        if self.socket is not None and self.socket.connected:
            self.print_debug("client <-- " + repr(args))
            try:
                self.socket.sendObjAsJSON(args)
            except BrokenPipeError:
                self.reconnectSocket()
                self.print("Broken pipe, connection dropped.")
        else:
            self.print_debug("nobody <-- " + repr(args))

    def sendStatusResponse(self, status, args=None):
        self.sendResponse('error', status, args)

    def sendEventResponse(self, event, args=None):
        self.sendResponse('event', event, args)

    def sendSuccessResponse(self, data=None):
        if data is None:
            self.sendStatusResponse('success')
        else:
            self.sendStatusResponse('success', {'data': data})

    def sendFailureResponse(self, message=None):
        if message is None:
            self.sendStatusResponse('failure')
        else:
            if type(message) != str:
                raise TypeError
            self.sendStatusResponse('failure', {'message': message})

    def playCurrentAndAdvance(self):
        # since hopefully there's no other way for mpv to emit a 'start-file' event
        # we set this now so once mpv gets the event, we can tell the client which
        # item is playing.
        current = self.state.getCurrentCuedName()
        if current is None:
            raise PlaylistStop
        self.mpv.play(current)
        self.state.setCurrentPlaying()
        self.state.advance()

    def requestReplacementVar(self, var):
        propReq = self.MPV_PROPERTY_REQUEST[var]
        self.mpv.sendCommand(propReq[0], [propReq[1]], request_id=propReq[2])

    def setReplacementVar(self, reqID, data):
        if self.neededProperties == None:
            raise RuntimeError("Got data from MPV but no properties needed.")
        prop = self.MPV_PROPERTY_SET[reqID]
        for neededProp in enumerate(self.neededProperties):
            if prop[0] == neededProp[1][0]:
                if prop[1] != None:
                    data = prop[1](data)
                if data == None:
                    self.neededProperties[neededProp[0]] = (prop[0], self.REPLACEMENT_NONE)
                else:
                    self.neededProperties[neededProp[0]] = (prop[0], data)

    def sendPlaylists(self):
        self.sendEventResponse('new-playlists', {'playlists': self.state.getPlaylists()})

    def sendPlaylist(self, pl):
        self.sendEventResponse('add-entries', {'playlist': pl.name, 'entries': pl.getEntries()})
        self.sendEventResponse('cue-item', {'playlist': pl.name, 'item': pl.currentCue})

    def sendMpvOpts(self):
        self.sendEventResponse('set-mpv-opts', {'opts': self.state.mpvopts})

    def sendProperties(self):
        props = []
        for prop in self.neededProperties:
            props.append(prop[1])
        self.sendEventResponse('get-properties', {'properties': props})

    def clientMpvUnexpectedTerminated(self):
        self.mpv.terminate()
        self.mpv = None
        self.connected = False
        self.playing = False
        self.sendEventResponse('mpv-unexpected-termination')

    def stop(self):
        self.state.stop()
        self.playing = False

    def tick(self):
        def checkPropertiesFilled():
            for prop in self.neededProperties:
                if prop[1] == None:
                    return
            self.sendProperties()
            self.neededProperties = None
        if self.neededProperties != None:
            checkPropertiesFilled()

        if self.mpv is not None:
            if self.mpv.checkMPVRunning():
                if self.mpv.socket is None:
                    if time.monotonic() - self.lastConnectionAttempt >= 1:
                        self.lastConnectionAttempt = time.monotonic()
                        try:
                            self.mpv.connect()
                        except ConnectionRefusedError:
                            self.print("Connection refused, socket not ready?")
                        except FileNotFoundError:
                            self.print("File not found, waiting on mpv...")
                else:
                    if not self.connected:
                        self.sendEventResponse("run-mpv")
                        self.connected = True
                    if self.neededProperties != None:
                        for prop in enumerate(self.neededProperties):
                            if prop[1][1] == None and prop[1][2] == False:
                                self.requestReplacementVar(prop[1][0])
                                self.neededProperties[prop[0]] = (prop[1][0], prop[1][1], True)
                    try:
                        obj = self.mpv.getNextObj()

                        if obj is not None:
                            self.print_debug("MPV --> " + repr(obj))
                            if 'event' in obj:
                                if obj['event'] == 'idle':
                                    if self.playing:
                                        try:
                                            self.playCurrentAndAdvance()
                                        except PlaylistStop:
                                            self.stop()
                                        except ValueError as e:
                                            self.stop()
                                            self.print("State error: " + e.args[0])
                                elif obj['event'] == 'start-file':
                                    self.playing = True
                            elif 'error' in obj:
                                if 'request_id' in obj:
                                    if obj['request_id'] != self.MPV_COMMAND_REQUEST_ID:
                                        if obj['error'] == 'success':
                                            self.setReplacementVar(obj['request_id'], obj['data'])
                                        else:
                                            self.setReplacementVar(obj['request_id'], None)
                                    else:
                                        if self.waitForCommand:
                                            if obj['error'] == 'success':
                                                self.sendEventResponse('mpv-command')
                                            else:
                                                self.sendFailureResponse("mpv-command: " + obj['error'])
                                            self.waitForCommand = False
                                        else:
                                            self.print("Got command response when not waiting for one?")
                    except ConnectionError as e:
                        self.print("MPV connection error: " + e.args[0])
                        self.clientMpvUnexpectedTerminated()
            else:
                self.print("MPV terminated unexpectedly.")
                self.clientMpvUnexpectedTerminated()
        else:
            if self.neededProperties != None:
                if self.socket.connected:
                    self.sendFailureResponse("get-properties: MPV terminated before all properties were gathered.")
                self.neededProperties = None
            if self.waitForCommand:
                if self.socket.connected:
                    self.sendFailureResponse("mpv-command: MPV terminated before response.")
                self.waitForCommand = False

        if not self.socket.connected:
            self.socket.accept()
        else:
            if self.lastAct is None:
                self.lastAct = time.monotonic()
            obj = None
            try:
                obj = self.socket.getJSONAsObj()
                self.lastAct = time.monotonic()
            except json.decoder.JSONDecodeError as e:
                self.sendFailureResponse("Bad JSON: " + e.args[0])
            except ConnectionError as e:
                self.print("Client connection error: " + e.args[0])
                self.reconnectSocket()
                return True
            if obj is None:
                if time.monotonic() - self.lastAct > MPVVJServer.TIMEOUT:
                    self.print("Client connection timed out!")
                    self.reconnectSocket()
            else:
                self.lastAct = time.monotonic()
                self.print_debug("client --> " + repr(obj))
                if 'command' in obj:
                    if obj['command'] == 'get-all-state':
                        self.sendPlaylists()
                        for pl in self.state.playlists:
                            if (len(pl.entries) != 0):
                                self.sendPlaylist(pl)
                        self.sendMpvOpts()
                    elif obj['command'] == 'get-version':
                        self.sendEventResponse(obj['command'], {'data': self.VERSION})
                    elif obj['command'] == 'set-mpv-opts':
                        command = obj['command']
                        del obj['command']
                        if 'opts' in obj:
                            if type(obj['opts']) == list:
                                def checkOptions(options):
                                    for opt in options:
                                        if type(opt) != list:
                                            self.sendFailureResponse(command + ": Option item is not a list.")
                                            return False
                                        if len(opt) != 2:
                                            self.sendFailureResponse(command + ": Option must contain the key and value.")
                                            return False
                                        if type(opt[0]) != str or type(opt[1]) != str:
                                            self.sendFailureResponse(command + ": Option keys and values must be strings.")
                                            return False
                                    return True
                                if checkOptions(obj['opts']):
                                    self.mpvopts = obj['opts']
                                    self.sendEventResponse(command)
                            else:
                                self.sendFailureResponse(command + ": 'opts' is not a list.")
                        else:
                            self.sendFailureResponse(command + ": No 'opts'.")
                    elif obj['command'] == 'run-mpv':
                        command = obj['command']
                        if self.mpv is None:
                            self.mpv = MPV.MPV(self.mpvPath, self.socketPath, self.mpvopts)
                            self.lastConnectionAttempt = time.monotonic()
                            # client gets notified once a connection to MPV is established
                        else:
                            self.sendFailureResponse(command + ": MPV is already running.")
                    elif obj['command'] == 'terminate-mpv':
                        command = obj['command']
                        self.terminateMpv()
                        self.sendEventResponse(command)
                    elif obj['command'] == 'new-playlists':
                        command = obj['command']
                        del obj['command']
                        ret = self.state.newPlaylists(obj)
                        if ret is not None:
                            self.sendFailureResponse(command + ": " + ret)
                        else:
                            self.sendEventResponse(command)
                    elif obj['command'] == 'delete-playlists':
                        command = obj['command']
                        del obj['command']
                        ret = self.state.deletePlaylists(obj)
                        if ret is not None:
                            self.sendFailureResponse(command + ": " + ret)
                        else:
                            self.sendEventResponse(command)
                    elif obj['command'] == 'select-playlist':
                        command = obj['command']
                        del obj['command']
                        ret = self.state.setSelectedPlaylist(obj)
                        if ret is not None:
                            self.sendFailureResponse(command + ": " + ret)
                        else:
                            self.sendEventResponse(command)
                    elif obj['command'] == 'toggle-looping':
                        command = obj['command']
                        del obj['command']
                        ret = self.state.togglePlaylistLooping()
                        if ret is not None:
                            self.sendFailureResponse(command + ": " + ret)
                        else:
                            self.sendEventResponse(command)
                    elif obj['command'] == 'toggle-shuffle':
                        command = obj['command']
                        del obj['command']
                        ret = self.state.togglePlaylistShuffle()
                        if ret is not None:
                            self.sendFailureResponse(command + ": " + ret)
                        else:
                            self.sendEventResponse(command)
                    elif obj['command'] == 'add-items':
                        command = obj['command']
                        del obj['command']
                        ret = self.state.addItems(obj)
                        if ret is not None:
                            self.sendFailureResponse(command + ": " + ret)
                        else:
                            self.sendEventResponse(command)
                    elif obj['command'] == 'delete-items':
                        command = obj['command']
                        del obj['command']
                        ret = self.state.deleteItems(obj)
                        if ret is not None:
                            self.sendFailureResponse(command + ": " + ret)
                        else:
                            self.sendEventResponse(command)
                    elif obj['command'] == 'set-played':
                        command = obj['command']
                        del obj['command']
                        ret = self.state.setPlayed(obj)
                        if ret is not None:
                            self.sendFailureResponse(command + ": " + ret)
                        else:
                            self.sendEventResponse(command)
                    elif obj['command'] == 'track-relative':
                        command = obj['command']
                        del obj['command']
                        ret = self.state.setPlaylistCurrentItemRelative(obj)
                        if ret is not None:
                            self.sendFailureResponse(command + ": " + ret)
                        else:
                            self.sendEventResponse(command)
                    elif obj['command'] == 'track-absolute':
                        command = obj['command']
                        del obj['command']
                        ret = self.state.setPlaylistCurrentItem(obj)
                        if ret is not None:
                            self.sendFailureResponse(command + ": " + ret)
                        else:
                            self.sendEventResponse(command)
                    elif obj['command'] == 'loop-file':
                        command = obj['command']
                        del obj['command']
                        ret = self.state.toggleFileLooping()
                        if ret is not None:
                            self.sendFailureResponse(command + ": " + ret)
                        else:
                            self.sendEventResponse(command)                    
                    elif obj['command'] == 'mpv-command':
                        command = obj['command']
                        if 'mpv' not in obj:
                            self.sendFailureResponse("No 'mpv'.")
                        self.mpv.sendCommand(obj['mpv'][0], obj['mpv'][1:], request_id=self.MPV_COMMAND_REQUEST_ID)
                        self.waitForCommand = True
                    elif obj['command'] == 'cue-playlist':
                        command = obj['command']
                        del obj['command']
                        ret = self.state.setCurrentPlaylist(obj)
                        if ret is not None:
                            self.sendFailureResponse(command + ": " + ret)
                        else:
                            self.sendEventResponse(command)
                    elif obj['command'] == 'play':
                        command = obj['command']
                        if self.mpv is not None:
                            try:
                                self.playCurrentAndAdvance()
                                self.playing = True
                                self.sendEventResponse(command)
                            except ValueError as e:
                                self.stop()
                                self.sendFailureResponse(command + ": " + e.args[0])
                            except PlaylistStop:
                                self.stop()
                                self.sendFailureResponse(command + ": End of playlist reached.")
                        else:
                            self.sendFailureResponse(command + ": MPV isn't running.")
                    elif obj['command'] == 'stop':
                        command = obj['command']
                        if self.playing:
                            self.mpv.stop()
                            self.playing = False
                            self.sendEventResponse(command)
                        else:
                            self.sendFailureResponse(command + ": Already stopped.")
                    elif obj['command'] == 'move-items':
                        command = obj['command']
                        del obj['command']
                        ret = self.state.moveItems(obj)
                        if ret is not None:
                            self.sendFailureResponse(command + ": " + ret)
                        else:
                            self.sendEventResponse(command)
                    elif obj['command'] == 'get-properties':
                        command = obj['command']
                        if 'properties' not in obj:
                            self.sendFailureResponse(command + ": No 'properties'.")
                        if type(obj['properties']) != list:
                            self.sendFailureResponse(command + ": 'properties' is not a list.")
                        if len(obj['properties']) == 0:
                            self.sendFailureResponse(command + ": 'properties' is empty.")
                        for prop in obj['properties']:
                            if type(prop) != str:
                                self.sendFailureResponse(command + ": Property is not a string.")
                        self.neededProperties = []
                        for prop in obj['properties']:
                            if prop == 'file':
                                try:
                                    name = self.state.getCurrentPlayingName()
                                    try:
                                        slash = name.rindex('/')
                                        self.neededProperties.append((prop, name[slash+1:]))
                                    except ValueError:
                                        self.neededProperties.append((prop, name))
                                except ValueError:
                                    self.neededProperties.append((prop, self.REPLACEMENT_NONE))
                            elif prop == 'path':
                                try:
                                    self.neededProperties.append((prop, self.state.getCurrentPlayingName()))
                                except ValueError:
                                    self.neededProperties.append((prop, self.REPLACEMENT_NONE))
                            elif prop == 'playlistlength':
                                try:
                                    self.neededProperties.append((prop, self.state.getCurrentPlaylistLength()))
                                except ValueError:
                                    self.neededProperties.append((prop, self.REPLACEMENT_NONE))
                            elif prop == 'position':
                                try:
                                    self.neededProperties.append((prop, self.state.getCurrentPlaylistPlayingPos()))
                                except ValueError:
                                    self.neededProperties.append((prop, self.REPLACEMENT_NONE))
                            elif prop == 'playlistslength':
                                try:
                                    self.neededProperties.append((prop, self.state.getPlaylistsCount()))
                                except ValueError:
                                    self.neededProperties.append((prop, self.REPLACEMENT_NONE))
                            elif prop == 'currentname':
                                try:
                                    self.neededProperties.append((prop, self.state.getCurrentPlaylistName()))
                                except ValueError:
                                    self.neededProperties.append((prop, self.REPLACEMENT_NONE))
                            elif prop == 'currentposition':
                                if self.state.currentPlaylist == None:
                                    self.neededProperties.append((prop, self.REPLACEMENT_NONE))
                                else:
                                    self.neededProperties.append((prop, self.state.currentPlaylist))
                            elif prop == 'selectedname':
                                try:
                                    self.neededProperties.append((prop, self.state.getSelectedPlaylistName()))
                                except ValueError:
                                    self.neededProperties.append((prop, self.REPLACEMENT_NONE))
                            elif prop == 'selectedposition':
                                if self.state.selectedPlaylist == None:
                                    self.neededProperties.append((prop, self.REPLACEMENT_NONE))
                                else:
                                    self.neededProperties.append((prop, self.state.selectedPlaylist))
                            elif prop == 'repeat':
                                try:
                                    self.neededProperties.append((prop, MPVVJUtils.boolYesNo(self.state.getCurrentPlaylistLooping())))
                                except ValueError:
                                    self.neededProperties.append((prop, self.REPLACEMENT_NONE))
                            elif prop == 'single':
                                self.neededProperties.append((prop, MPVVJUtils.boolYesNo(self.state.loopFile)))
                            else:
                                if prop not in self.MPV_PROPERTY_REQUEST:
                                    self.sendFailureResponse(command + ": Unrecognized property: " + prop)
                                    self.neededProperties = None
                                    break
                                else:
                                    self.neededProperties.append((prop, None, False))
                    elif obj['command'] == 'list':
                        command = obj['command']
                        playlists = self.state.getPlaylists()
                        playlist = self.state.getPlaylist()
                        currentPlaylist = self.state.currentPlaylist
                        playingPlaylist = self.state.playingPlaylist
                        selectedPlaylist = self.state.selectedPlaylist
                        selectedCued = None
                        try:
                            selectedCued = self.state.getSelectedPlaylistCuedPos()
                        except ValueError:
                            pass
                        selectedPlaying = None
                        try:
                            selectedPlaying = self.state.getSelectedPlaylistPlayingPos()
                        except ValueError:
                            pass

                        resp = {'playlists': playlists, 'current-playlist': currentPlaylist, 'playing-playlist': playingPlaylist, 'selected-playlist': selectedPlaylist, 'cued': selectedCued, 'playing': selectedPlaying}

                        if playlist != None:
                            resp['playlist'] = playlist

                        self.sendEventResponse(command, resp)
                    elif obj['command'] == 'clear':
                        command = obj['command']
                        self.state = MPVVJState.MPVVJState()
                        self.sendEventResponse(command)
                    elif obj['command'] == 'kill':
                        command = obj['command']
                        self.sendEventResponse(command)
                        self.cleanUp()
                        return False
                    else:
                        self.sendFailureResponse("Unknown action!")
                else:
                    self.sendFailureResponse("JSON statement with nothing to do!")
        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MPV-VJ3 - Remotely control mpv and manage playlists.")
    parser.add_argument('-q', '--quiet', action='store_true', help="Suppress all text output.")
    parser.add_argument('-v', '--verbose', action='store_true', help="Verbose output.")
    parser.add_argument('--mpv-path', metavar="<PATH>", type=str,
                        help="Path to MPV executable.", default=DEFAULT_MPV)
    parser.add_argument('--mpv-socket-path', metavar="<PATH>", type=str,
                        help="Filename of socket to use for communicating with mpv.",
                        default=DEFAULT_SOCKET)
    parser.add_argument('--bind-address', metavar="<address>", type=str,
                        help="Address to bind to.", default=DEFAULT_BIND_ADDRESS)
    parser.add_argument('--bind-port', metavar="<port>", type=int,
                        help="Port to bind to.", default=DEFAULT_PORT)
    args = parser.parse_args()

    server = MPVVJServer(args.mpv_path, args.mpv_socket_path,
                         args.bind_address, args.bind_port,
                         args.quiet, args.verbose)
    random.seed(time.time())

    try:
        while server.tick():
            time.sleep(1 / TPS)
    except BaseException as e:
        server.cleanUp()
        raise e
