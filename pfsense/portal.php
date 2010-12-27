<?php 

require_once("functions.inc");
$clientip = $_SERVER['REMOTE_ADDR'];
/* find MAC address for client */
$clientmac = arp_get_mac_by_ip($clientip);

$orig_request = $_GET['redirurl'];
if (preg_match("/redirurl=(.*)/", $orig_request, $matches))
    $redirurl = urldecode($matches[1]);
if ($_POST['redirurl'])
    $redirurl = $_POST['redirurl'];
?>

<html>
  <body>
    <script type="text/javascript">
      window.location.href = "https://hd-wifi.appspot.com/<?= base64_encode(str_replace(":", "", $clientmac) .','. $redirurl); ?>";
    </script>
  </body>
</html>