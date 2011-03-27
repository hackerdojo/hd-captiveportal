from pyrad import dictionary, packet, server
import logging
import sys
import urllib2
import threading

logger = logging.getLogger("pyrad")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

member_cache = {}

class RadiusServer(server.Server):
    """ Simple RADIUS server bridge 
    
    This is assumed to be used with the pfSense captive portal service, 
    configured to send the MAC address of the client as the username. It
    simply hits up the hd-wifi app to see if the MAC address can get online
    and optionally with what bandwidth limitations.
    """
    
    def HandleAuthPacket(self, pkt):
        def _handle():
            mac_address = pkt[1][0]
            reply=self.CreateReplyPacket(pkt)
            try:
                resp = urllib2.urlopen('http://hd-captiveportal.appspot.com/api/mac/%s' % mac_address)
                user, download, upload = resp.read().split(',')
                if download:
                    reply.AddAttribute((14122,8), download) # WISPr-Bandwidth-Max-Down
                if upload:
                    reply.AddAttribute((14122,7), upload) # WISPr-Bandwidth-Max-Up
                if not '*' in user:
                    member_cache[mac_address] = user
                reply.code=packet.AccessAccept
                print "accept: %s %s %s %s" % (mac_address, user, download, upload)
            except (urllib2.URLError, urllib2.HTTPError), e:
                if hasattr(e, 'code') and e.code == 404:
                    reply.code=packet.AccessReject
                    print "reject: %s" % mac_address
                else:
                    if mac_address in member_cache:
                        reply.AddAttribute((14122,8), '0')
                        reply.AddAttribute((14122,7), '0')
                        print "accept [failover]: %s %s" % (mac_address, member_cache[mac_address])
                    else:
                        print "accept [failover]: %s" % mac_address
                    reply.code=packet.AccessAccept
                    
            self.SendReplyPacket(pkt.fd, reply)
        thread = threading.Thread(target=_handle)
        thread.start()


srv=RadiusServer(addresses=[''], dict=dictionary.Dictionary("dictionary"))
srv.hosts["127.0.0.1"]=server.RemoteHost("127.0.0.1", "secret", "localhost")

logger.info("starting server...")
try:
    srv.Run()
except KeyboardInterrupt:
    sys.exit(0)
