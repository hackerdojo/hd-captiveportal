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
import time
import string

DOMAIN = 'hackerdojo.com'
MEMBER_DOWNLOAD = 0
MEMBER_UPLOAD = 0
GUEST_TIMEOUT = 43200 # 12 hours
#GUEST_TIMEOUT = 60
GUEST_NAME = 'internet-guest*'
DAYPASS_NAME = 'internet-daypass*'
DEFAULT_REDIRECT = 'http://hackerdojo.com'
DONATE_BUTTON = '6JB7VARJDVHAG'

def dojo(path, force=False):
    """ Hacker Dojo Domain API helper with caching """
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

def is_suspended(user):
    """ Convenience function for if a user is suspended """
    return dojo('/users/%s' % user)['suspended']

def touch_stat(name, resolution=60):
    """ Keeps a backlog of counts for calculating rate """
    bucket = '%s-%s' % (name, int(time.time()) - int(time.time()) % resolution)
    if not memcache.add(bucket, 0, time=resolution*5):
        memcache.incr(bucket)

def get_stat(name, resolution=60):
    """ Calculate running average of a stat from counts """
    since = time.time() - (resolution*5)
    since = int(since) - int(since) % resolution
    keys = ['%s-%s' % (name, since + (i * resolution)) for i in range(5-1)]
    counts = memcache.get_multi(keys).values()
    if len(counts):
        return sum(counts) / len(counts)
    else:
        return 0

class Login(db.Model):
    """ A non log of logins. """
    
    address = db.StringProperty()
    username = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)


class MacAddressMapping(db.Model):
    """ Member MAC address mapping
    
    Simple record indicating a user successfully authenticated as a member
    using a particular MAC address. This is used when the RADIUS bridge asks
    if a MAC address can get online.
    """
    
    address = db.StringProperty()
    username = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    
    @classmethod
    def register_new_device(cls, address, username):
        total_devices = 2
        devices = cls.all().filter('username =', username).order("-created").fetch(100)
        for d in devices[total_devices-1:]:
          d.delete()
        m = cls(address=address, username=username)
        m.put()
        return m
    

    @classmethod
    def get_by_mac(cls, address):
        return cls.all().filter('address =', address).get()


class LogHandler(webapp.RequestHandler):
    """ Show log  """
    
    def get(self):   
        log = Login.all()
        self.response.out.write(template.render('templates/log.html', {
            'log': log
        }))


class EntryHandler(webapp.RequestHandler):
    """ Entry point for the wifi app
    
    The pfSense Captive Portal page (as defined in pfsense/portal.php) will
    redirect to this endpoint. It will encode the user's MAC address and 
    final redirect URL as a base64 encoded string as part of the path.
    """
    
    def get(self, data):   
        try:
            data = urllib.unquote(data)
            mac, redirect = base64.b64decode(data).split(',')
            self.response.out.write(template.render('templates/main.html', {
                'redirect': redirect,
                'mac': mac,
                'error': self.request.get('error')
            }))
        except:
            self.error(400)
            self.response.out.write("bad request")
    
class MemberHandler(webapp.RequestHandler):
    """ Form handler when connecting as a member """
    
    def post(self):
        client = AppsService(domain=DOMAIN)
        username = string.split(self.request.get('username'),"@")[0].strip()
        mac = self.request.get('mac')
        redirect = self.request.get('redirect')
        try:
            client.ClientLogin('%s@%s' % (username, DOMAIN), self.request.get('password').strip())
            login = Login(username=username, address = mac)
            login.put()
            existing = MacAddressMapping.get_by_mac(mac)
            if existing and not is_suspended(username):
                self.redirect(redirect or DEFAULT_REDIRECT)
            elif not is_suspended(username):
                MacAddressMapping.register_new_device(mac,username)
                self.redirect(redirect or DEFAULT_REDIRECT)
            else:
                raise Exception("Invalid account")
        except Exception, e:
            self.redirect('/%s?error=%s' % (base64.b64encode(','.join([mac, redirect])), e.message))

class GuestHandler(webapp.RequestHandler):
    """ Form handler when connecting as a guest """
    
    def get(self):
        memcache.set(self.request.get('mac'), GUEST_NAME, time=GUEST_TIMEOUT)
        self.redirect(self.request.get('redirect') or DEFAULT_REDIRECT)

class DonateHandler(webapp.RequestHandler):
    """ Form handler when donating for a day pass """
    
    def get(self):
        mac = self.request.get('mac')
        redirect = self.request.get('redirect') or DEFAULT_REDIRECT
        callback = "%s/donate/%s" % (self.request.host_url, base64.b64encode(','.join([mac, redirect])))
        memcache.set(mac, GUEST_NAME, time=GUEST_TIMEOUT)
        self.redirect("https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=%s&notify_url=%s&return=%s" %
            (DONATE_BUTTON, callback, callback))

class DonateCallbackHandler(webapp.RequestHandler):
    """ Callback handler for PayPal IPN (POST) and return from PayPal (GET) """
    
    def post(self, data):
        data = urllib.unquote(data)
        mac, redirect = base64.b64decode(data).split(',')
        if self._validate_ipn() and self.request.get('payment_status').lower() == 'completed':
            memcache.set(mac, DAYPASS_NAME, time=GUEST_TIMEOUT)
        self.get(data)
    
    def _validate_ipn(self):
        resp = urlfetch.fetch('https://www.paypal.com/cgi-bin/webscr', method="POST",
            payload="cmd=_notify-validate&%s" % self.request.body)
        return "VERIFIED" in resp.content
    
    def get(self, data):
        data = urllib.unquote(data)
        mac, redirect = base64.b64decode(data).split(',')
        if not redirect.startswith('http'):
            redirect = DEFAULT_REDIRECT
        self.response.out.write(template.render('templates/daypass.html', {'hours': GUEST_TIMEOUT/3600, 'redirect': redirect}))

class MacHandler(webapp.RequestHandler):
    """ Endpoint used by RADIUS bridge """
    
    def get(self, mac):
        guest = memcache.get(mac)
        if guest:
            if guest == DAYPASS_NAME:
                self.response.out.write("%s,%s,%s" % (guest, MEMBER_DOWNLOAD, MEMBER_UPLOAD))
            else:
                self.response.out.write("%s,," % guest)
            touch_stat('guests')
        else:
            mapping = MacAddressMapping.get_by_mac(mac)
            if mapping and not is_suspended(mapping.username):
                self.response.out.write("%s,%s,%s" % (mapping.username, MEMBER_DOWNLOAD, MEMBER_UPLOAD))
                touch_stat('members')
            else:
                self.error(404)
                self.response.out.write("not found")

class StatHandler(webapp.RequestHandler):
    """ Simple endpoint for getting current members/guests using Internet """
    
    def get(self, name=None):
        if name in ['members', 'guests']:
            stat = get_stat(name)
        else:
            members = get_stat('members')
            guests = get_stat('guests')
            stat = members+guests
        self.response.out.write(str(stat))

class DevHandler(webapp.RequestHandler):
    """ Convenience entry point for local development """
    
    def get(self):
        self.response.out.write(template.render('templates/dev.html', {}))
    
    def post(self):
        self.redirect('/%s' % base64.b64encode(','.join([
            self.request.get('mac'), 
            self.request.get('redirect')])))

def main():
    application = webapp.WSGIApplication([
        ('/dev', DevHandler),
        ('/log', LogHandler),
        ('/api/mac/(.+)', MacHandler),
        ('/api/stat/(.+)', StatHandler),
        ('/guest', GuestHandler),
        ('/donate/(.+)', DonateCallbackHandler),
        ('/donate', DonateHandler),
        ('/member', MemberHandler),
        ('/(.+)', EntryHandler),] ,debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
