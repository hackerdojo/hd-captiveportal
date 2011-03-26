<?php 
/**
 * pfSense Captive Portal page
 *
 * This file is intended to be uploaded to pfSense under the captive portal
 * service as the captive portal page. It simply gets the intended URL for
 * eventual redirection, gets the client MAC address, encodes them in a base64
 * string, then redirects to the hd-wifi app on App Engine. 
 *
 * It's assumed the pfSense captive portal "allowed IP addresses" includes the 
 * IP of the hd-wifi app. 
 *
 * The PHP script this will override in pfSense is available here:
 * http://cvs.pfsense.org/cgi-bin/cvsweb.cgi/pfSense/usr/local/captiveportal/index.php
 */

require_once("functions.inc");

$orig_request = $_GET['redirurl'];
if (preg_match("/redirurl=(.*)/", $orig_request, $matches))
    $redirurl = urldecode($matches[1]);
if ($_POST['redirurl'])
    $redirurl = $_POST['redirurl'];

$clientip = $_SERVER['REMOTE_ADDR'];
$clientmac = arp_get_mac_by_ip($clientip);    

?>

<html>
  <body>
    <script type="text/javascript">
      window.location.href = "https://hd-captiveportal.appspot.com/<?= base64_encode(str_replace(":", "", $clientmac) .','. $redirurl); ?>";
    </script>
  </body>
</html>