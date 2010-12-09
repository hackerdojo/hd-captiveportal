from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import util, template
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from django.utils import simplejson
from gdata.apps.service import AppsService
import logging
import base64

DOMAIN = 'hackerdojo.com'

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

class MainHandler(webapp.RequestHandler):
    def get(self, data):
        try:
            mac, redirect = base64.b64decode(data).split(',')
            self.response.out.write(template.render('templates/main.html', {
                'redirect': redirect,
                'mac': mac,
            }))
        except:
            self.error(400)
    
    def post(self, data):
        client = AppsService(domain=DOMAIN)
        try:
            client.ClientLogin('%s@%s' % (self.request.get('username'), DOMAIN), self.request.get('password'))
            if not dojo('/users/%s' % self.request.get('username'))['suspended']:
                memcache.set(self.request.get('mac'), self.request.get('username'))
                self.redirect(self.request.get('redirect'))
            else:
                raise Exception()
        except:
            self.redirect('/%s' % data)


class MacHandler(webapp.RequestHandler):
    def get(self, mac):
        user = memcache.get(mac)
        if not user or dojo('/users/%s' % user)['suspended']:
            self.error(404)
            self.response.out.write("not found")
        else:
            self.response.out.write(user)
        

def main():
    application = webapp.WSGIApplication([
        ('/api/mac/(.+)', MacHandler),
        ('/(.+)', MainHandler),],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
