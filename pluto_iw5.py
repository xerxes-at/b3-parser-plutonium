#
# BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2005 Michael "ThorN" Thornton
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#
# CHANGELOG
#
# 23/09/2017 - 0.1 - Xerxes - parser created
# ??/11/2017 - 0.2 - Xerxes - Fixed the parser for status.
# ??/12/2017 - 0.3 - Xerxes - Fixed it again.
# ??/12/2017 - 0.4 - Xerxes - Replaced the ping for Bots with 999.
# ??/12/2017 - 0.5 - Xerxes - Cleaned up the result of getCvar.
# 06/04/2018 - 0.6 - Xerxes - Removed unused code.

__author__ = 'Xerxes'
__version__ = '0.6'

import b3.parsers.cod8
import re

from threading import Timer

class Pluto_Iw5Parser(b3.parsers.cod8.Cod8Parser):

    gameName = 'PlutoIW5'
    _botPrefix = "FFFFFFFF000B07"
    _guidLength = 16
    _line_length = 43
    _commands = {
        'message': 'tell %(cid)s %(message)s', #gib cmd
        'say': 'say %(message)s',
        'set': 'set %(name)s "%(value)s"',
        'kick': 'dropClient %(cid)s %(reason)s',
        'ban': 'dropClient %(cid)s %(reason)s',
        'unban': 'unban %(name)s',
        'tempban': 'dropClient %(cid)s %(reason)s'
    }
    
    _reMapNameFromStatus = re.compile(r'^map:\s+(?P<map>[a-z0-9_-]+).*$', re.IGNORECASE)
    
    #Please don't hate me too much for this regex its 05:38 (AM).
    #This regex might cause cancer if you try to access the clantag, you might wanna trim it.
    #_regPlayer = re.compile(r'^(?P<slot>[0-9]+).*?(?P<ping>\d+|---)\s+.*?\s+(?P<name>.*?)\s+(?P<ip>[0-9.+|localhost)([:]*)(?P<port>[0-9-]+|)\s+(?P<score>[0-9-]+).*$', re.IGNORECASE)
    #_regPlayer = re.compile(r'^(?P<slot>[0-9]+).*?(?P<ping>\d+|---)\s+?(?P<tag>.+?|\s+?)(?P<name>[a-zA-Z0-9]*?)\s+(?P<ip>[0-9.]+|localhost)([:]*)(?P<port>[0-9-]+|)\s+(?P<score>[0-9-]+).*$', re.IGNORECASE)
    #Still NO IPv6 support :((
    #Check tags!
    _regPlayer = re.compile(r'^(?P<slot>[0-9]+).+?(?P<ping>\d+|---)\s+?(?P<tag>.+?|\s+?)(?P<name>\S+)\s+(?P<ip>[0-9.]+|localhost)([:]*)(?P<port>[0-9-]+|)\s+(?P<score>[0-9-]+).*$', re.IGNORECASE)

    ####################################################################################################################
    #                                                                                                                  #
    #   PARSER INITIALIZATION                                                                                          #
    #                                                                                                                  #
    ####################################################################################################################

    def startup(self):
        """
        Called after the parser is created before run().
        """
        b3.parsers.cod8.Cod8Parser.startup(self)

    ####################################################################################################################
    #                                                                                                                  #
    #   EVENT HANDLERS                                                                                                 #
    #                                                                                                                  #
    ####################################################################################################################
    
    #Remove the guid from bots.
    def OnJ(self, action, data, match=None):
        codguid = match.group('guid')
        cid = match.group('cid')
        name = match.group('name')
        if len(codguid) < self._guidLength:
            # invalid guid
            self.verbose2('Invalid GUID: %s. GUID length set to %s' % (codguid, self._guidLength))
            codguid = None

        if codguid != None and codguid.startswith(self._botPrefix):
            # We have a bot
            self.info('Changed GUID from %s to NONE since it matches the bot prefix' % codguid)
            codguid = None
        client = self.getClient(match)

        if client:
            self.verbose2('Client object already exists')
            # lets see if the name/guids match for this client, prevent player mixups after mapchange (not with PunkBuster enabled)
            if codguid != client.guid:
                self.debug('This is not the correct client (%s <> %s): disconnecting...' % (codguid, client.guid))
                client.disconnect()
                return None
            else:
                self.verbose2('client.guid in sync: %s == %s' % (codguid, client.guid))

            client.state = b3.STATE_ALIVE
            client.name = name
            # join-event for mapcount reasons and so forth
            return self.getEvent('EVT_CLIENT_JOIN', client=client)
        else:
            if self._counter.get(cid) and self._counter.get(cid) != 'Disconnected':
                self.verbose('cid: %s already in authentication queue: aborting join' % cid)
                return None

            self._counter[cid] = 1
            t = Timer(2, self.newPlayer, (cid, codguid, name))
            t.start()
            self.debug('%s connected: waiting for authentication...' % name)
            self.debug('Our authentication queue: %s' % self._counter)
    
    ####################################################################################################################
    #                                                                                                                  #
    #   B3 PARSER INTERFACE IMPLEMENTATION                                                                             #
    #                                                                                                                  #
    ####################################################################################################################
    
    #Give bots a ping of 999 instead of '---'
    def getPlayerPings(self, filter_client_ids=None):
        """
        Returns a dict having players' id for keys and players' ping for values.
        :param filter_client_ids: If filter_client_id is an iterable, only return values for the given client ids.
        """
        data = self.write('status')
        if not data:
            return {}

        players = {}
        for line in data.split('\n'):
            m = re.match(self._regPlayerShort, line)
            if not m:
                m = re.match(self._regPlayer, line.strip())
            
            if m:
                ping = 999
                if m.group('ping') != '---':
                    # We don't have a bot
                    ping = int(m.group('ping'))
                players[str(m.group('slot'))] = ping
        
        return players
        
    def getCvar(self, cvar_name):
        """
        Return a CVAR from the server.
        :param cvar_name: The CVAR name.
        """
        if self._reCvarName.match(cvar_name):
            val = self.write(cvar_name).replace("\"^7","\"").repalce("\x00","")
            self.debug('Get cvar %s = [%s]', cvar_name, val)

            m = None
            for f in self._reCvar:
                m = re.match(f, val)
                if m:
                    break

            if m:
                if m.group('cvar').lower() == cvar_name.lower():
                    try:
                        default_value = m.group('default')
                    except IndexError:
                        default_value = None
                    return b3.cvar.Cvar(m.group('cvar'), value=m.group('value'), default=default_value)
            else:
                return None