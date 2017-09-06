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

def parseKeyValues(opts):
    optsList = []
    for opt in opts:
        try:
            equals = opt.index('=')
            optsList.append((opt[:equals], opt[equals+1:]))
        except ValueError:
            optsList.append((opt, 'yes'))

    return optsList

def parseRanges(items):
    if type(items) != str:
        raise TypeError
    itemList = []

    while len(items) > 0:
        try:
            comma = items.index(',')
            try:
                dash = items.index('-')
                start = int(items[:dash])
                end = int(items[dash+1:comma])
                if start < end:
                    temp = start
                    start = end
                    end = temp
                itemList.extend(range(start, end))
            except ValueError: #single value
                itemList.append(int(items[:dash]))
            items = items[comma+1:]
        except ValueError: #no comma, last entry
            try:
                dash = items.index('-')
                start = int(items[:dash])
                end = int(items[dash+1:comma])
                if start < end:
                    temp = start
                    start = end
                    end = temp
                itemList.extend(range(start, end))
            except ValueError: #single value
                itemList.append(int(items))
            items = ''

    return itemList

def parseTime(time):
    sign = 1

    if time[0] == '-':
        sign = -1
        time = time[1:]
    elif time[0] == '+':
        time = time[1:]

    try:
        colon1 = time.rindex(':')
        try:
            colon2 = time.rindex(':')
            return ((int(time[:colon2]) * 60 * 60)
                    (int(time[colon2+1:colon1]) * 60) +
                    int(time[colon1+1:])) * sign
        except ValueError:
            return ((int(time[:colon1]) * 60) +
                    int(time[colon1+1:])) * sign
    except ValueError:
        return int(time) * sign

def toTime(secs):
    if secs == None:
        return None

    secs = float(secs)

    sign = 1
    if secs < 0:
        sign = -1
        secs = -secs

    hours = int(secs / 60 / 60) * sign
    mins = int(secs / 60 % 60)
    secs = int(secs % 60)

    return "{}:{:02}:{:02}".format(hours, mins, secs)

def toPreciseTime(secs):
    if secs == None:
        return None

    secs = float(secs)

    sign = 1
    if secs < 0:
        sign = -1
        secs = -secs

    hours = int(secs / 60 / 60) * sign
    mins = int(secs / 60 % 60)
    secs = secs % 60

    return "{}:{:02}:{:02}".format(hours, mins, secs)

def boolYesNo(boolval):
    if boolval == True:
        return 'yes'
    elif boolval == False:
        return 'no'

    return None

def statusStr(status):
    if status == True:
        return "Paused"
    elif status == False:
        return "Playing"

    return None

def roundTenth(val):
    if val == None:
        return None

    return str(round(float(val), 1))

def numDigits(num):
    digits = 1
    while num >= 10:
        num /= 10
        digits += 1

    return digits
