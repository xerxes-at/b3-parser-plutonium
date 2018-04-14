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
# 06/04/2018 - 0.6 - Xerxes - Removed unused code.
# 06/04/2018 - 0.5 - Xerxes - Added the maximum line lengh for say and tell.
# 06/04/2018 - 0.4 - Xerxes - Fixed a crash due to the logging on our custom setter for the GUID.
# 06/04/2018 - 0.3 - Xerxes - Replaced broken CMDs with working ones.
# 06/04/2018 - 0.2 - Xerxes - Patched the GUID setter of the clients so we can use very short guids, also set the minimal length for guid.
# 17/03/2018 - 0.1 - Xerxes - parser created.

__author__ = 'Xerxes'
__version__ = '0.6'

import b3.parsers.pluto_iw5
import re

from threading import Timer

class Pluto_T6Parser(b3.parsers.pluto_iw5.Pluto_Iw5Parser):

    gameName = 'PlutoT6'
    _botGuid = "0"
    _guidLength = 1
    _line_length = 72
    _commands = {
        'message': 'tell %(cid)s %(message)s',
        'say': 'say %(message)s',
        'set': 'set %(name)s "%(value)s"',
        'kick': 'clientkick %(cid)s',
        'ban': 'clientkick %(cid)s',
        'unban': 'unban %(name)s',
        'tempban': 'clientkick %(cid)s'
    }
    
    _reCvar = re.compile(r'^((?P<cvar>[a-z][a-z0-9_]*)).*?(is).*?(\")(?P<value>.*)(\")', re.IGNORECASE)
    _regPlayer = re.compile(r'^\s*?(?P<slot>[0-9]+)\s+?(?P<score>[0-9-]+).+?(?P<bot>\d+)\s+?(?P<ping>\d+|)\s+?(?P<guid>\S+)\s+?\^7(?P<name>[\S\s]+?)\s+?(?P<last>\d+)\s+?(?P<ip>[0-9.]+|localhost)[:]*(?P<port>[0-9-]+|)\s+?(?P<qport>[0-9-]+).+?(?P<rate>\d+)', re.IGNORECASE)
    
    ####################################################################################################################
    #                                                                                                                  #
    #   PARSER INITIALIZATION                                                                                          #
    #                                                                                                                  #
    ####################################################################################################################

    def startup(self):
        """
        Called after the parser is created before run().
        """
        b3.parsers.pluto_iw5.Pluto_Iw5Parser.startup(self)
        #Add our own expressions to the line formats.
        #Kill + Damage
        self._lineFormats = (
        re.compile(r'(?P<action>[A-Z]);(?P<data>(?P<guid>[^;]+);(?P<cid>[0-9]{1,2});(?P<team>[a-z]*);(?P<name>[^;]+);(?P<aguid>[^;]+);(?P<acid>[0-9-]{1,2});(?P<ateam>[a-z]*);(?P<aname>[^;]+);(?P<aweap>[a-z0-9_+-]+);(?P<damage>[0-9.]+);(?P<dtype>[A-Z_]+);(?P<dlocation>[a-z_]+))$', re.IGNORECASE),
        
        ) + self._lineFormats

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
        self.verbose2('Client Joining: %s: %s [%s]' % (name, codguid,cid))
        if len(codguid) < self._guidLength:
            # invalid guid
            self.verbose2('Invalid GUID: %s. GUID length set to %s' % (codguid, self._guidLength))
            codguid = None

        if codguid != None and codguid == self._botGuid:
            # We have a bot
            self.info('Changed GUID to NONE for %s.' % name)
            codguid = None
        client = self.getClient(match)

        if client:
            self.verbose2('Client object already exists')
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
        
    def getCvar(self, cvar_name):
        """
        Return a CVAR from the server.
        :param cvar_name: The CVAR name.
        """
        if self._reCvarName.match(cvar_name):
            val = self.write("get " + cvar_name).replace("\"^7","\"")
            self.debug('Get cvar %s = [%s]', cvar_name, val)

            m = re.match(self._reCvar, val)

            if m:
                if m.group('cvar').lower() == cvar_name.lower():
                    try:
                        default_value = m.group('default')
                    except IndexError:
                        default_value = None
                    return b3.cvar.Cvar(m.group('cvar'), value=m.group('value'), default=default_value)
            else:
                return None
                
    def cod9ClientGuidSetter(self, guid):
        if self.console != None:
            self.console.verbose2('Custom setter works. :ok:') 
        if guid and len(guid) > 0:
            if self._guid and self._guid != guid:
                if self.console != None:
                    self.console.error('Client has guid but its not the same %s <> %s', self._guid, guid)
                self.authed = False
            elif not self._guid:
                if self.console != None:
                    self.console.verbose2('Set guid from %s to %s', self._guid, guid)
                self._guid = guid
        else:
            self.authed = False
            self._guid = ''
                
    b3.clients.Client.guid = property(b3.clients.Client._get_guid, cod9ClientGuidSetter)