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


import random
import time


class PlaylistEntry:
    def __init__(self, name, played=False):
        if type(name) != str or type(played) != bool:
            raise TypeError
        self.name = name
        self.played = played

    def __eq__(self, value):
        return self.name == value

    def setPlayed(self, value):
        if type(value) != bool:
            raise TypeError
        self.played = value


class Playlist:
    def __init__(self, name, loop, shuffle):
        if type(name) != str or type(loop) != bool or type(shuffle) != bool:
            raise TypeError
        self.name = name
        self.items = []
        self.playingItem = None
        self.currentCue = None
        self.loop = loop
        self.shuffle = shuffle

    def __len__(self):
        return len(self.items)

    def __contains__(self, key):
        for item in self.items:
            if item == key:
                return True
        return False

    def __getitem__(self, key):
        for item in enumerate(self.items):
            if item[1] == key:
                return item
        return KeyError

    def __delitem__(self, key):
        item = self[key]
        del self.items[item[0]]

    def insertEntry(self, value, played=False, idx=-1):
        empty = False
        if len(self) == 0:
            empty = True

        if idx < 0:
            self.items.append(PlaylistEntry(value, played))
        else:
            self.items.insert(idx, PlaylistEntry(value, played))

        if empty:
            if self.shuffle:
                self.currentCue = random.randrange(len(self))
            else:
                self.currentCue = 0

    def noneEntryByIndex(self, idx):
        self.items[idx] = None
        if self.currentCue != None:
            if idx == self.currentCue:
                self.currentCue = -1
            elif idx < self.currentCue:
                self.currentCue -= 1

    def deleteNones(self):
        while True:
            try:
                idx = self.items.index(None)
                del self.items[idx]
            except ValueError:
                break

    def getItems(self):
        items = []
        for item in self.items:
            items.append({'name': item.name, 'played': item.played})

        return items

    def setCurrent(self, idx):
        if idx < 0 or idx > len(self.items) - 1:
            raise IndexError

        self.currentCue = idx

    def getCurrentItemName(self):
        if self.currentCue == None:
            return None
        return self.items[self.currentCue].name

    def getPlayingItemName(self):
        if self.playingItem == None:
            return None
        return self.items[self.playingItem].name

    def setCurrentPlaying(self):
        self.playingItem = self.currentCue

    def stop(self):
        self.playingItem = None

    def advance(self):
        if len(self) == 0:
            raise ValueError("Empty playlist.")

        # this function is only used for advancing after something has been played
        # so set this now
        self.items[self.currentCue].setPlayed(True)

        if self.shuffle:
            notPlayed = []
            for item in enumerate(self.items):  # select an entry that hasn't been played
                if not item[1].played:
                    notPlayed.append(item[0])

            if len(notPlayed) == 0:
                if self.loop:
                    for item in self.items:
                        item.setPlayed(False)
                        self.currentCue = random.randrange(len(self))
                else:
                    self.currentCue = None
            else:
                self.currentCue = notPlayed[random.randrange(len(notPlayed))]
        else:
            if self.currentCue == len(self) - 1:
                if self.loop:
                    for item in self.items:
                        item.setPlayed(False)
                    self.currentCue = 0
                else:
                    self.currentCue = None
            else:
                self.currentCue += 1

    def setLooping(self, value=None):
        if value == None:
            self.loop = not self.loop
        else:
            if type(value) != bool:
                raise TypeError
            self.loop = value

    def setShuffle(self, value=None):
        if value == None:
            self.shuffle = not self.shuffle
        else:
            if type(value) != bool:
                raise TypeError
            self.shuffle = value

    def setPlayed(self, index, value):
        self.items[index].setPlayed(value)


class MPVVJState:
    def __init__(self):
        self.playlists = []
        self.selectedPlaylist = None
        self.currentPlaylist = None
        self.playingPlaylist = None
        self.interPlaylist = None
        self.TVMainTime = 0
        self.TVInterTime = 0
        self.loopFile = False
        self.TVMode = False
        self.lastMain = None
        self.lastInter = None

    def __contains__(self, key):
        for pl in self.playlists:
            if pl.name == key:
                return True
        return False

    def __getitem__(self, key):
        for pl in enumerate(self.playlists):
            if pl[1].name == key:
                return pl
        raise KeyError

    def getSelected(self):
        if self.selectedPlaylist == None:
            return None
        return self.playlists[self.selectedPlaylist]

    def getCurrent(self):
        if self.currentPlaylist == None:
            return None
        return self.playlists[self.currentPlaylist]

    def getPlaying(self):
        if self.playingPlaylist == None:
            return None
        return self.playlists[self.playingPlaylist]

    def getInter(self):
        if self.interPlaylist == None:
            return None
        return self.playlists[self.interPlaylist]

    def newPlaylist(self, name, loop, random):
        self.playlists.append(Playlist(name, loop, random))

    def newPlaylists(self, obj):
        if 'playlists' not in obj:
            return "No 'playlists'."
        if type(obj['playlists']) != list:
            return "'playlists' is not a list."
        for item in enumerate(obj['playlists']):
            if type(item[1]) != dict:
                return "'playlists' item not a dict."
            if 'name' not in item[1]:
                return "'playlists' item with no 'name'."
            if type(item[1]['name']) != str:
                return "'name' is not a string."
            try:
                if type(item[1]['loop']) != bool:
                    return "'loop' is not a bool."
            except KeyError:
                pass
            try:
                if type(item[1]['shuffle']) != bool:
                    return "'shuffle' is not a bool."
            except KeyError:
                pass

            if item[1]['name'] in self:
                return "Playlist item '" + item[1]['name'] + "' already exists."
            for item2 in enumerate(obj['playlists']):
                if item[0] == item2[0]:
                    continue
                if item[1]['name'] == item2[1]['name']:
                    return "Duplicate name '" + item[1]['name'] + "'."

        for item in obj['playlists']:
            loop = False
            shuffle = False
            try:
                loop = item['loop']
            except KeyError:
                pass
            try:
                shuffle = item['shuffle']
            except KeyError:
                pass

            self.newPlaylist(item['name'], loop, shuffle)
        return None

    def deletePlaylist(self, idx):
        if self.currentPlaylist != None:
            if self.currentPlaylist == idx:
                self.currentPlaylist = None
            elif self.currentPlaylist > idx:
                self.currentPlaylist -= 1

        if self.selectedPlaylist != None:
            if self.selectedPlaylist == idx:
                self.selectedPlaylist = None
            elif self.selectedPlaylist > idx:
                self.selectedPlaylist -= 1

        if self.playingPlaylist != None:
            if self.playingPlaylist == idx:
                self.playingPlaylist = None
            elif self.playingPlaylist > idx:
                self.playingPlaylist -= 1

        if self.interPlaylist != None:
            if self.interPlaylist == idx:
                self.interPlaylist = None
            elif self.interPlaylist > idx:
                self.interPlaylist -= 1

        del self.playlists[idx]

    def deletePlaylists(self, obj):
        if 'playlists' not in obj:
            return "No 'playlists' list."
        if type(obj['playlists']) != list:
            return "'playlists' is not a list."
        indices = []
        for item in obj['playlists']:
            if type(item) != str:
                return "'playlists' item not a string."
            pl = None
            try:
                pl = self[item]
            except KeyError:
                return "Playlist " + item + " does not exist."
            indices.append(pl[0])

        for idx in indices:
            self.deletePlaylist(idx)
        return None

    def setSelectedPlaylist(self, obj):
        if 'playlist' not in obj:
            return "No 'playlist'."
        if obj['playlist'] is None:
            self.selectedPlaylist = None
            return None
        if type(obj['playlist']) != str:
            return "'playlist' is not a string."
        pl = None
        try:
            pl = self[obj['playlist']]
        except KeyError:
            return "Playlist " + obj['playlist'] + " does not exist."

        self.selectedPlaylist = pl[0]
        return None

    def togglePlaylistLooping(self):
        selected = self.getSelected()
        if selected == None:
            return "No playlist selected."
        selected.setLooping()
        return None

    def togglePlaylistShuffle(self):
        selected = self.getSelected()
        if selected == None:
            return "No playlist selected."
        selected.setShuffle()
        return None

    def addItems(self, obj):
        selected = self.getSelected()
        if selected == None:
            return "No playlist selected."
        if 'items' not in obj:
            return "No 'items'."
        if type(obj['items']) != list:
            return "'items' is not a list."
        location = len(selected)
        try:
            if type(obj['location']) != int:
                return "'location' is not an integer."
            else:
                location = obj['location']
                playlistLen = len(selected)
                if location < -playlistLen - 1 or location > playlistLen:
                    return "'location'=" + str(location) + " out of range."
        except KeyError:
            pass
        for item in obj['items']:
            if type(item) != dict:
                return "Item is not a dict."
            if 'name' not in item:
                return "Item with no 'name'."
            if type(item['name']) != str:
                return "'name' is not a string."
            try:
                if type(item['played']) != bool:
                    return "'played' is not a bool."
            except KeyError:
                pass

        for item in obj['items']:
            played = False
            try:
                played = item['played']
            except KeyError:
                pass

            selected.insertEntry(item['name'], played, location)
            if location >= 0:
                location += 1
            else:
                location -= 1
        return None

    def deleteItems(self, obj):
        selected = self.getSelected()
        if selected == None:
            return "No playlist selected."
        if 'items' not in obj:
            return "No 'items' list."
        if type(obj['items']) != list:
            return "'items' is not a list."
        for item in obj['items']:
            if type(item) != int:
                return "Item is not an integer."
            if item < 0 or item > len(selected) - 1:
                return "Item " + str(item) + " out of range."

        for item in obj['items']:
            selected.noneEntryByIndex(item)
        selected.deleteNones()
        return None

    def setPlaylistCurrentItemRelative(self, obj):
        selected = self.getSelected()
        if selected == None:
            return "No playlist selected."
        if 'item' not in obj:
            return "No 'item'."
        if type(obj['item']) != int:
            return "'item' is not an integer."
        current = selected.currentCue
        relPos = current + obj['item']
        if relPos < 0 or relPos > len(selected) - 1:
            return "current=" + str(current) + " + 'item'=" + str(obj['item']) + " = " + str(relPos) + " out of range."

        selected.setCurrent(relPos)
        return None

    def setPlaylistCurrentItem(self, obj):
        selected = self.getSelected()
        if selected == None:
            return "No playlist selected."
        if 'item' not in obj:
            return "No 'item'."
        if type(obj['item']) != int:
            return "'item' is not an integer."
        if obj['item'] < 0 or obj['item'] > len(selected) - 1:
            return "'item'=" + str(obj['item']) + " out of range."

        selected.setCurrent(obj['item'])
        return None

    def setCurrentPlaylist(self, obj):
        if 'playlist' not in obj:
            return "No 'playlist'."
        if obj['playlist'] is None:
            self.currentPlaylist = None
            return None
        if type(obj['playlist']) != str:
            return "'playlist' is not a string."
        pl = None
        try:
            pl = self[obj['playlist']]
        except KeyError:
            return "Playlist " + obj['playlist'] + " does not exist."
        if len(pl[1]) == 0:
            return "Playlist " + obj['playlist'] + " has no entries."

        self.currentPlaylist = pl[0]
        return None

    def moveItems(self, obj):
        selected = self.getSelected()
        if selected == None:
            return "No playlist selected."
        if 'items' not in obj:
            return "No 'items'."
        if type(obj['items']) != list:
            return "'items' is not a list."
        if len(obj['items']) == 0:
            return "'items' is an empty list."

        playlist = None
        try:
            if obj['playlist'] != None and type(obj['playlist']) != str:
                return "'playlist' is not a string or None."
            try:
                playlist = obj['playlist']
            except KeyError:
                return obj['playlist'] + " does not exist."
        except KeyError:
            pass

        if playlist == None:        
            playlist = selected
        else:
            playlist = self[playlist][1]

        srcPlaylistLen = len(selected)
        destPlaylistLen = len(playlist)

        location = len(playlist)
        try:
            if type(obj['location']) != int:
                return "'location' is not an integer."
            else:
                location = obj['location']
                if location < -destPlaylistLen - 1 or location > destPlaylistLen:
                    return "'location'=" + str(location) + " out of range."
        except KeyError:
            pass        

        for item in obj['items']:
            if type(item) != int:
                return "Item is not an int."
                if item < -srcPlaylistLen or item > srcPlaylistLen - 1:
                    return "Item=" + item + " out of range."
                if self.selectedPlaylist == playlist:
                    if location >= 0 and location >= item:
                        location -= 1
                    elif location < 0 and location <= -(srcPlaylistLen - item) - 1:
                        location += 1

        items = []
        for item in obj['items']:
            items.append(selected.items[item])
            selected.noneEntryByIndex(item)
        selected.deleteNones()

        for item in items:
            playlist.insertEntry(item.name, False, location)
            if location >= 0:
                location += 1
            else:
                location -= 1
        return None

    def getPlaylists(self):
        playlists = []
        for pl in self.playlists:
            playlists.append({'name': pl.name, 'current': pl.currentCue, 'loop': pl.loop, 'shuffle': pl.shuffle})

        return playlists

    def getPlaylist(self):
        selected = self.getSelected()
        if selected == None:
            return None

        return selected.getItems()

    def setPlayed(self, obj):
        selected = self.getSelected()
        if selected == None:
            return "No playlist selected."
        if 'items' not in obj:
            return "No 'item'."
        if type(obj['items']) != list:
            return "'items' is not a list."
        playlistLen = len(selected)
        for item in obj['items']:
            if type(item) != int:
                return "Item isn't an int."
            if item < -playlistLen or item > playlistLen - 1:
                return "Index " + str(item) + " is out of range."

        value = None
        try:
            if type(obj['value']) != bool:
                return "'value' is not a bool."
            value = obj['value']
        except KeyError:
            pass
        for item in obj['items']:
            selected.setPlayed(item, value)
        return None

    def getCurrentCuedName(self):
        if self.TVMode:
            if self.lastMain != None or (self.lastMain == None and self.lastInter == None):
                try:
                    return self.getCurrent().getCurrentItemName()
                except AttributeError:
                    raise ValueError("No current playlist cued.")
            elif self.lastInter != None:
                try:
                    return self.getInter().getCurrentItemName()
                except AttributeError:
                    raise ValueError("No current playlist cued.")
        try:
            return self.getCurrent().getCurrentItemName()
        except AttributeError:
            raise ValueError("No current playlist cued.")

    def getCurrentPlayingName(self):
        try:
            return self.getPlaying().getPlayingItemName()
        except AttributeError:
            raise ValueError("Nothing playing.")

    def getCurrentPlaylistLength(self):
        try:
            return len(self.getCurrent())
        except AttributeError:
            raise ValueError("No current playlist cued.")

    def getCurrentPlaylistCuedPos(self):
        try:
            return self.getCurrent().currentCue
        except AttributeError:
            raise ValueError("No current playlist cued.")

    def getCurrentPlaylistPlayingPos(self):
        try:
            return self.getCurrent().playingItem
        except AttributeError:
            raise ValueError("No current playlist cued.")

    def getSelectedPlaylistCuedPos(self):
        try:
            return self.getSelected().currentCue
        except AttributeError:
            raise ValueError("No current playlist cued.")

    def getSelectedPlaylistPlayingPos(self):
        try:
            return self.getSelected().playingItem
        except AttributeError:
            raise ValueError("No current playlist cued.")

    def getPlaylistsCount(self):
        return len(self.playlists)

    def getCurrentPlaylistName(self):
        try:
            return self.getCurrent().name
        except AttributeError:
            raise ValueError("No current playlist cued.")

    def getSelectedPlaylistName(self):
        try:
            return self.getSelected().name
        except AttributeError:
            raise ValueError("No selected playlist.")

    def getCurrentPlaylistLooping(self):
        try:
            return self.getCurrent().loop
        except AttributeError:
            raise ValueError("No selected playlist.")

    def toggleFileLooping(self):
        self.loopFile = not self.loopFile

    def setCurrentPlaying(self):
        if self.TVMode:
            if self.lastMain != None or (self.lastMain == None and self.lastInter == None):
                try:
                    self.getCurrent().setCurrentPlaying()
                except AttributeError:
                    raise ValueError("No current playlist cued.")
                self.playingPlaylist = self.currentPlaylist
                return
            elif self.lastInter != None:
                try:
                    self.getInter().setCurrentPlaying()
                except AttributeError:
                    raise ValueError("No intermission playlist selected.")
                self.playingPlaylist = self.interPlaylist
                return
        try:
            self.getCurrent().setCurrentPlaying()
        except AttributeError:
            raise ValueError("No current playlist cued.")
        self.playingPlaylist = self.currentPlaylist

    def setIntervals(self, main, inter):
        if type(main) != int or type(inter) != int:
            return "Interval is not an int."
        if main < 0 or inter < 0:
            return "Intervals must be greater than or equal to 0."
        self.TVMainTime = main
        self.TVInterTime = inter

        return None

    def setInterPlaylist(self, playlist):
        if type(playlist) != str:
            return "Playlist is not a string."
        pl = None
        try:
            pl = self[playlist]
        except KeyError:
            return "Playlist " + playlist + " does not exist."

        self.interPlaylist = pl[0]
        return None

    def toggleTVMode(self):
        inter = self.getInter()
        if inter == None:
            raise ValueError("No intermission playlist selected.")        
        self.TVMode = not self.TVMode
        self.lastInter = None
        self.lastMain = None

    def stop(self):
        try:
            self.getPlaying().stop()
        except AttributeError:
            raise ValueError("No current playlist cued.")
        self.playingPlaylist = None

    def advance(self):
        current = self.getCurrent()
        if current == None:  # no playlist selected
            raise ValueError("No playlist selected.")
        if self.loopFile:
            return
        if self.TVMode:
            inter = self.getInter()
            if inter == None:
                raise ValueError("No intermission playlist selected.")
            if self.lastMain != None:
                if time.monotonic() - self.lastMain < self.TVMainTime:
                    current.advance()
                else:
                    inter.advance()
                    self.lastInter = time.monotonic()
                    self.lastMain = None
                return
            elif self.lastInter != None:
                if time.monotonic() - self.lastInter < self.TVInterTime:
                    inter.advance()
                else:
                    current.advance()
                    self.lastMain = time.monotonic()
                    self.lastInter = None
                return
            else:
                current.advance()
                self.lastMain = time.monotonic()
                return

        current.advance()

