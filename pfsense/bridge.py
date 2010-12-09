from pyrad import dictionary, packet, server
import logging
import sys
import urllib2

logger = logging.getLogger("pyrad")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

class RadiusServer(server.Server):
    def HandleAuthPacket(self, pkt):
        mac_address = pkt[1][0]
        reply=self.CreateReplyPacket(pkt)
        try:
            resp = urllib2.urlopen('http://hd-wifi.appspot.com/api/mac/%s' % mac_address)
            print "success"
            reply.code=packet.AccessAccept
        except:
            print "fail"
            reply.code=packet.AccessReject
        self.SendReplyPacket(pkt.fd, reply)


srv=RadiusServer(addresses=[''], dict=dictionary.Dictionary("dictionary"))
srv.hosts["66.92.0.185"]=server.RemoteHost("66.92.0.185", "secret", "localhost")

logger.info("starting server...")
try:
    srv.Run()
except KeyboardInterrupt:
    sys.exit()
