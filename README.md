
# How it works

pfSense has a captive portal service that will capture all packets
unless you are authorized. It will capture any HTTP requests and
redirect you to a special page served by pfSense (see
pfsense/portal.php). However, this page simply uses pfSense functions to
map your requesting IP to a MAC address. Then it takes this MAC address
and the URL you were trying to go to, base64 encodes them, and passes
that information to an App Engine app via redirect.

The App Engine app serves a page that lets members login for full
access, or lets guests get a daypass or use the guest network. This app
keeps this state for pfSense to check if you are authorized.

The way pfSense finds out if you are authorized is using a RADIUS
server. This is the only workable option pfSense gives us. So we have a
"fake" RADIUS server running on pfSense (see pfsense/bridge.py) that
takes authorization packets and checks with the App Engine app if that
MAC is authorized. It keeps a local cache and has a fail over mechanism,
but otherwise it's just a bridge to let us do authorization with the App
Engine app that has that state.

The App Engine app has some tricky logic that is worth pointing out.
When you login as a member, it will authorize against Google Apps. This
may return a captcha challenge, which we have to pass on to the user. If
they successfully login, we create a Login record and a
MacAddressMapping. Recall, the MAC address was passed in from the
pfSense captive portal PHP page. The app actually stores this in a
cookie for easy access later. 

Now that there is a MacAddressMapping (and there can only be a limited
number of mappings per member), when the RADIUS bridge asks if a MAC
address is authorized, we lookup the MacAddressMapping, make sure the
member is not suspended, then authorize by returning 200 and some
configuration that's passed back to pfSense (namely bandwidth
limitations).

The app handles guest logins slightly differently. When you connect as a
guest, daypass or not, we do not use a MacAddressMapping, but a simple
memcache key using the MAC address as the key. This makes it easy to
expire and keeps member mappings separate from guest mappings. When a
guest purchases a day pass, we set the value to signify they are a
day pass user. Otherwise, we signify they are just a guest.

So when the RADIUS bridge asks the app if a MAC is authorized, it will
first check memcache to see if they are a guest or day pass holder
before checking for member MacAddressMappings. It will return
appropriately depending on which they are, including their bandwidth
limitations.

# Debugging

## Resetting your device

If you logged in as a guest, you can just go to the root path (/) of the
App Engine app and it will clear your cookie and its memcache record of
you. If you are logged in as a member, you will have to use the App
Engine admin to delete the MacAddressMapping record. 

In either case, you will also have to remove a record from pfSense under
Status > Captive Portal. Then you should be reset. You have to delete
both the record in App Engine and pfSense for reset to happen correctly.
