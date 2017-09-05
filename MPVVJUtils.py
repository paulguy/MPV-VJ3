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
            optsList.append(opt, 'yes')

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
                itemList.append(int(items[:comma]))
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
