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

import argparse
import sys

import MPVVJRequest


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = "12345"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MPV-VJ3 - Remotely control mpv and manage playlists with an mpvc-like interface.", epilog="""<playlist> refers to a name of a playlist.
<range> refers to a comma separated list of single values or ranges denoted by <start>-<end>.
<format string> refers to a string containing replacement strings for various values.  These include
%file% %path% %title% %artist% %album% %artistalbum% %genre% %year% %status% %time% %precisetime% %length% %percentage% %speed% %playlistlength %position% %repeat% %single% %volume% %muted% %frame%.
<time> refers to an absolute time in HH:MM:SS, MM:SS or SS format.  Absolute times may be negative for some files.
<reltime> refers to a relative time in HH:MM:SS, MM:SS or SS format.  Reverse using negative values.
May be called with no arguments for a generic status output.""")
    clientopts = parser.add_argument_group(title="Client Options")
    clientopts.add_argument('--quiet', action='store_true', help="Suppress all text output.")
    clientopts.add_argument('--verbose', action='store_true', help="Verbose output.")
    clientopts.add_argument('--address', metavar="<address>", type=str,
                        help="Address to connect to.", default=DEFAULT_HOST)
    clientopts.add_argument('--port', metavar="<port>", type=int,
                        help="Port to connect to.", default=DEFAULT_PORT)
    mpvacts = parser.add_argument_group(title="MPV Actions")
    mpvacts.add_argument('-O', '--mpv-opts', type=str, nargs=argparse.REMAINDER, help="Set mpv arguments.  Must be last option.  Format: <option[=value]> [option[=value]] ...")
    mpvacts.add_argument('-r', '--run', action='store_true', help="Run MPV.")
    mpvacts.add_argument('-k', '--kill', action='store_true', help="Kill MPV.")
    playlistacts = parser.add_argument_group(title="Playlist Actions")
    playlistacts.add_argument('-n', '--new', type=str, metavar="<name>", help="Add a new playlist.")
    playlistacts.add_argument('-D', '--delete', type=str, metavar="<playlist>", help="Delete a playlist.")
    playlistacts.add_argument('-e', '--select', type=str, metavar="<playlist>", help="Select playlist to operate on.")
    playlistacts.add_argument('-l', '--loop', type=str, metavar="<playlist>", help="Toggle playlist loop mode.")
    playlistacts.add_argument('-z', '--shuffle', type=str, metavar="<playlist>", help="Toggle playlist shuffle mode.")
    playlistacts.add_argument('-a', '--add', type=str, nargs=argparse.REMAINDER, help="Add files to selected playlist.  Must be last option.  Note the files need to be available from the remote mpv's location.")
    playlistacts.add_argument('-d', '--delete-items', metavar="<range>", type=str, help="Delete items from playlist.")
    playlistacts.add_argument('-M', '--move', type=str, help="Move items from selected playlist.  Format: <range>.[playlist,]pos>")
    playlistacts.add_argument('-y', '--set-played', type=str, metavar="<range>", help="Flag files as played.")
    playlistacts.add_argument('-Y', '--set-not-played', type=str, metavar="<range>", help="Flag files as not played.")
    playlistacts.add_argument('-j', '--track', type=int, help="Go forwards/backwards through the playlist queue.")
    playlistacts.add_argument('-J', '--tracknum', type=int, help="Jump to playlist item number.")
    playbackacts = parser.add_argument_group(title="Playback Actions")
    playbackacts.add_argument('-L', '--loopfile', action='store_true', help="Loop currently playing file.")
    playbackacts.add_argument('-t', '--seek', type=str, metavar="<reltime>", help="Increase/decrease time relative to the current time.")
    playbackacts.add_argument('-T', '--time', type=str, metavar="<time>", help="Set absolute time.")
    playbackacts.add_argument('-v', '--vol', type=int, help="Increase/decrease volume relative to the current volume.")
    playbackacts.add_argument('-V', '--volume', type=int, help="Set absolute volume.")
    playbackacts.add_argument('-m', '--mute', action='store_true', help="Toggle muting.")
    playbackacts.add_argument('-c', '--cue', type=str, metavar="<playlist>", help="Cue a playlist to play from next.")
    playbackacts.add_argument('-P', '--play', action='store_true', help="Play next cued item.")
    playbackacts.add_argument('-s', '--stop', action='store_true', help="Always stop playback.")
    playbackacts.add_argument('-p', '--toggle', action='store_true', help="Toggle playback.")
    infoacts = parser.add_argument_group(title="Information Actions")
    infoacts.add_argument('-f', '--format', type=str, metavar="<format string>", help="Enter a formatting string.")
    infoacts.add_argument('-S', '--list', action='store_true', help="Print all playlists and tracks in selected playlist.")
    serveracts = parser.add_argument_group(title="Server Actions")
    serveracts.add_argument('--clear', action='store_true', help="Clear all server state.")
    serveracts.add_argument('--kill-server', action='store_true', help="Kill server.")

    args = parser.parse_args()

    request = MPVVJRequest.MPVVJRequest(args.quiet, args.verbose)
    def try_connect(request, host, port, quiet):
        try:
            request.connect(host, port)
        except ConnectionRefusedError:
            if not quiet:
                print("Connection Failed: Connection Refused!")
                return False
        except ConnectionError as e:
            if not quiet:
                print("Connection error: " + e.args[0])
                return False
        return True

    response = True
    if try_connect(request, args.address, args.port, args.quiet):
        try:
            if (args.mpv_opts or args.run or args.kill or args.new or args.delete or
                args.select or args.loop or args.shuffle or args.add or args.delete_items or
                args.move or args.set_played or args.set_not_played or args.track != None or args.tracknum != None or
                args.loopfile or args.seek or args.time or args.vol != None or args.volume != None or
                args.mute or args.cue or args.play or args.stop or args.toggle or
                args.format or args.list or args.clear or args.kill_server):
                if args.mpv_opts:
                    request.mpvOpts(args.mpv_opts)
                    response = request.waitForResponse()
                if response == True and args.run:
                    request.run()
                    response = request.waitForResponse()
                if response == True and args.kill:
                    request.kill()
                    response = request.waitForResponse()
                if response == True and args.new:
                    request.newPlaylist(args.new)
                    response = request.waitForResponse()
                if response == True and args.delete:
                    request.deletePlaylist(args.delete)
                    response = request.waitForResponse()
                if response == True and args.select:
                    request.selectPlaylist(args.select)
                    response = request.waitForResponse()
                if response == True and args.loop:
                    request.loop(args.loop)
                    response = request.waitForResponse()
                if response == True and args.shuffle:
                    request.shuffle(args.shuffle)
                    response = request.waitForResponse()
                if response == True and args.add:
                    request.addItems(args.add)
                    response = request.waitForResponse()
                if response == True and args.delete_items:
                    request.deleteItems(args.delete_items)
                    response = request.waitForResponse()
                if response == True and args.move:
                    request.move(args.move)
                    response = request.waitForResponse()
                if response == True and args.set_played:
                    request.setPlayed(args.set_played)
                    response = request.waitForResponse()
                if response == True and args.set_not_played:
                    request.setNotPlayed(args.set_not_played)
                    response = request.waitForResponse()
                if response == True and args.track != None:
                    request.track(args.track)
                    response = request.waitForResponse()
                if response == True and args.tracknum != None:
                    request.trackNum(args.tracknum)
                    response = request.waitForResponse()
                if response == True and args.loopfile:
                    request.loopFile()
                    response = request.waitForResponse()
                if response == True and args.seek:
                    request.seek(args.seek)
                    response = request.waitForResponse()
                if response == True and args.time:
                    request.time(args.time)
                    response = request.waitForResponse()
                if response == True and args.vol != None:
                    request.vol(args.vol)
                    response = request.waitForResponse()
                if response == True and args.volume != None:
                    request.volume(args.volume)
                    response = request.waitForResponse()
                if response == True and args.mute:
                    request.mute()
                    response = request.waitForResponse()
                if response == True and args.cue:
                    request.cue(args.cue)
                    response = request.waitForResponse()
                if response == True and args.play:
                    request.play()
                    response = request.waitForResponse()
                if response == True and args.stop:
                    request.stop()
                    response = request.waitForResponse()
                if response == True and args.toggle:
                    request.toggle()
                    response = request.waitForResponse()
                if response == True and args.format:
                    request.format(args.format)
                    response = request.waitForResponse()
                if response == True and args.list:
                    request.list()
                    response = request.waitForResponse()
                if response == True and args.clear:
                    request.clear()
                    response = request.waitForResponse()
                if response == True and args.kill_server:
                    request.killServer()
                    response = request.waitForResponse()
            else:
                request.status()
                response = request.waitForResponse()
        except ConnectionError as e:
            if not args.quiet:
                print("Connection lost: " + e.args[0])
    else:
        sys.exit(2)

    request.disconnect()

    if response == False:
        sys.exit(1)
    sys.exit(0)
