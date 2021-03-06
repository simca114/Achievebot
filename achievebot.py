#Copyright (c) 2014 David Harwood

#Licensed under the terms of the MIT license
#http://opensource.org/licenses/MIT

#Twisted imports
from twisted.internet import ssl, reactor, protocol
from twisted.words.protocols import irc

#system imports
import time, sys, argparse, re
from ConfigParser import RawConfigParser

class AchievementHandler:
    """
    The class that handles the actual achievements, who gets them, who doesn't, etc.
    """

    achievefile = 'achievements'
    userfile = 'users'

    def __init__(self, config):
        #TODO: read config file, make settings changes as needed
        #more will be added here when there are acutally some options defined
        pass

    def command(self, user, channel, msg):
        try:
            parse = msg.strip().split(None, 1)
            if len(parse) < 2:
                return getattr(self, parse[0])()
            else:
                return getattr(self, parse[0])(parse[1])
        except:
            return ('msg', 'What?')

    def _achname(self, achievement):
        for line in open(self.achievefile, 'r'):
            if line.partition(' : ')[0].lower() == achievement.lower():
                return line.partition(' : ')[0]
        return None

    def grant(self, grant_block):
        user, achievement = grant_block.split(None, 1)
        if not self._achname(achievement):
            return ('msg', 'Achievement not found!')
        if achievement.lower() in self.earned(user)[1].lower():
            return ('msg', 'Achievement already earned')
        with open(self.userfile, 'a') as record:
            record.write('%s -> %s\n' % (user, self._achname(achievement)))
            record.flush()
        return ('notice', 'Achievement unlocked! %s has earned the achievement %s!' % (user, achievement))

    def earned(self, user):
        earned = ', '.join([ line.strip().split(None, 2)[2] for line in open(self.userfile, 'r') if line.split()[0] == user ])
        return ('msg', 'User %s has earned %s' % (user, earned))

    def add(self, achieve_block):
        parts = achieve_block.split(' : ')
        if len(parts) < 2:
            return ('msg', 'Achievement not added (I need at least a name and a description, more info optional)')
        if self._achname(parts[0]):
            return ('msg', 'Achievement not added: achievement with that name already exists!')
        with open(self.achievefile, 'a') as achievements:
            achievements.write(achieve_block + '\n')
            achievements.flush()
        return ('msg', 'Added new achievement: %s' % (parts[0]))

    def listachieve(self):
        achievements = ', '.join([ line.split(' : ', 1)[0] for line in open(self.achievefile, 'r') ])
        return ('msg', 'List of achievements: %s' % (achievements))

    def info(self, achievement):
        for line in open(self.achievefile, 'r'):
            if line.partition(' : ')[0].lower() == achievement.lower():
                parts = line.strip().split(' : ')
                if len(parts) == 2:
                    return ('msg', '%s: %s' % (parts[0], parts[1]))
                else:
                    return ('msg', '%s: %s (%s)' % (parts[0], parts[1], parts[2]))
        return ('msg', 'Achievement not found!')

    def help(self):
        script = ['I am Achievebot, made to track IRC achievements',
                'Commands:',
                'grant <user> <achievement> -> Grant achievement to user',
                'earned <user> -> Display all of the achievements the user has earned',
                'listachieve -> List all available achievements',
                'add <name> : <description> : <how to earn> -> Add a new achievement to the system (<how to earn> is optional)',
                'info <achievement> -> Show the full block of info on the specified achievement',
                'help -> Display this help',
                'join <channel> -> Join the specified channel',
                'leave <channel> -> Leave the specified channel',
                'quit -> Quit IRC',
                'More information and source code can be found at https://github.com/dharwood/Achievebot']
        return ('msg', '\n'.join(script))

class AchieveBot(irc.IRCClient):
    """
    An IRC bot to grant and keep track of achievements users earn.
    """

    nickname = "achievebot"
    lineRate = 0.2

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.achieve = AchievementHandler(self.factory.appopts)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)

    def privmsg(self, user, channel, msg):
        user = user.split('!', 1)[0]
        if channel == self.nickname:
            self.command(user, user, msg)
        elif msg.startswith(self.nickname):
            self.command(user, channel, msg.split(None, 1)[1])

    def command(self, user, channel, msg):
        if msg.startswith("quit"):
            self.quit(message="I have been told to leave")
        elif msg.startswith("join"):
            parts = msg.split()
            if len(parts) > 2:
                self.join(parts[1], key=parts[2])
            else:
                self.join(msg.split()[1])
        elif msg.startswith("leave"):
            self.leave(msg.split()[1], reason="I've been told to part")
        else:
            vol, output = self.achieve.command(user, channel, msg)
            getattr(self, vol)(channel, output)

class AchieveBotFactory(protocol.ClientFactory):
    """
    A factory for AchieveBots.
    """

    protocol = AchieveBot

    def __init__(self, config, ircopts, appopts):
        self.config = config
        self.ircopts = ircopts
        self.appopts = appopts

    def clientConnectionLost(self, connector, reason):
        reactor.stop()
        #reconnect if connection lost
        #connector.connect()


    def clientConnectionFailed(self, connector, reason):
        reactor.stop()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Bot for IRC achievements')
    parser.add_argument('-c', '--config', default='abot.conf', metavar='FILE', help='Config file to use. If it is missing, a default configuration file will be generated at the same path.')
    parser.add_argument('-s', '--server', help='Server to connect to (overrides config file)')
    parser.add_argument('-p', '--port', type=int, help='Port to connect to (overrides config file)')
    parser.add_argument('--ssl', action='store_true', help='Connect using SSL (overrides config file)')
    args = parser.parse_args()

    conf = RawConfigParser()
    try:
        conf.read(args.config)
        serv = conf.get('Connection', 'server')
        port = conf.getint('Connection', 'port')
        usessl = conf.getboolean('Connection', 'usessl')
    except:
        print("Configuration file can't be read. Generating.")
        conf.add_section('Connection')
        conf.set('Connection', 'server', 'INSERT VALUE HERE')
        conf.set('Connection', 'port', '6667')
        conf.set('Connection', 'usessl', 'no')
        conf.add_section('IRC Options')
        conf.add_section('Achievement Options')
        conf.write(open(args.config, 'wb'))
        print("Add IRC server address before using.")
        sys.exit()

    if args.server is not None:
        serv = args.server
    if args.port is not None:
        port = args.port
    if args.ssl:
        usessl = True

    f = AchieveBotFactory(args.config, dict(conf.items('IRC Options')), dict(conf.items('Achievement Options')))
    if usessl:
        reactor.connectSSL(serv, port, f, ssl.CertificateOptions())
    else:
        reactor.connectTCP(serv, port, f)
    reactor.run()

