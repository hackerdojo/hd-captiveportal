from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import util, template
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from django.utils import simplejson
from gdata.apps.service import AppsService
import logging
import base64
import urllib

DOMAIN = 'hackerdojo.com'
MEMBER_DOWNLOAD = 0
MEMBER_UPLOAD = 0
GUEST_DOWNLOAD = 1024
GUEST_UPLOAD = 384

# Hacker Dojo Domain API helper with caching
def dojo(path, force=False):
    base_url = 'http://domain.hackerdojo.com'
    cache_ttl = 3600
    resp = memcache.get(path)
    if force or not resp:
        resp = urlfetch.fetch(base_url + path, deadline=10)
        try:
            resp = simplejson.loads(resp.content)
        except Exception, e:
            resp = []
            cache_ttl = 10
        memcache.set(path, resp, cache_ttl)
    return resp

class MacAddressMapping(db.Model):
    address = db.StringProperty()
    username = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    
    @classmethod
    def get_by_mac(cls, address):
        return cls.all().filter('address =', address).get()

class MainHandler(webapp.RequestHandler):
    def get(self, data):   
        try:
            data = urllib.unquote(data)
            mac, redirect = base64.b64decode(data).split(',')
            self.response.out.write(template.render('templates/main.html', {
                'redirect': redirect,
                'mac': mac,
                'failure': self.request.get('fail')
            }))
        except:
            self.error(400)
            self.response.out.write("bad request")
    
    def post(self, data):
        client = AppsService(domain=DOMAIN)
        data = urllib.unquote(data)
        try:
            client.ClientLogin('%s@%s' % (self.request.get('username'), DOMAIN), self.request.get('password'))
            if not dojo('/users/%s' % self.request.get('username'))['suspended']:
                m = MacAddressMapping(address=self.request.get('mac'), username=self.request.get('username'))
                m.put()
                self.redirect(self.request.get('redirect') or 'http://hackerdojo.com')
            else:
                raise Exception()
        except:
            self.redirect('/%s?fail=1' % data)


class MacHandler(webapp.RequestHandler):
    def get(self, mac):
        mapping = MacAddressMapping.get_by_mac(mac)
        if not mapping or dojo('/users/%s' % mapping.username)['suspended']:
            self.error(404)
            self.response.out.write("not found")
        else:
            self.response.out.write("%s,%s,%s" % (mapping.username, MEMBER_DOWNLOAD, MEMBER_UPLOAD))
        

def main():
    application = webapp.WSGIApplication([
        ('/api/mac/(.+)', MacHandler),
        ('/(.+)', MainHandler),],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
