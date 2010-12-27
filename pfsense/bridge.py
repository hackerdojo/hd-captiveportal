from pyrad import dictionary, packet, server
import logging
import sys
import urllib2

logger = logging.getLogger("pyrad")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

class RadiusServer(server.Server):
    """ Simple RADIUS server bridge 
    
    This is assumed to be used with the pfSense captive portal service, 
    configured to send the MAC address of the client as the username. It
    simply hits up the hd-wifi app to see if the MAC address can get online
    and optionally with what bandwidth limitations.
    """
    
    def HandleAuthPacket(self, pkt):
        mac_address = pkt[1][0]
        reply=self.CreateReplyPacket(pkt)
        try:
            resp = urllib2.urlopen('http://hd-wifi.appspot.com/api/mac/%s' % mac_address)
            user, download, upload = resp.read().split(',')
            if download:
                reply.AddAttribute((14122,8), download) # WISPr-Bandwidth-Max-Down
            if upload:
                reply.AddAttribute((14122,7), upload) # WISPr-Bandwidth-Max-Up
            reply.code=packet.AccessAccept
            print "success: %s %s %s %s" % (mac_address, user, download, upload)
        except:
            reply.code=packet.AccessReject
            print "fail: %s" % mac_address
        self.SendReplyPacket(pkt.fd, reply)


srv=RadiusServer(addresses=[''], dict=dictionary.Dictionary("dictionary"))
srv.hosts["66.92.0.185"]=server.RemoteHost("66.92.0.185", "secret", "localhost")

logger.info("starting server...")
try:
    srv.Run()
except KeyboardInterrupt:
    sys.exit(0)
