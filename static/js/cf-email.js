/* Cloudflare-compatible email obfuscation decoder (XOR hex in data-cfemail). */
(function () {
  function decode(hex) {
    if (!hex || hex.length < 2) return "";
    var key = parseInt(hex.slice(0, 2), 16);
    var email = "";
    for (var i = 2; i < hex.length; i += 2) {
      email += String.fromCharCode(parseInt(hex.slice(i, i + 2), 16) ^ key);
    }
    return email;
  }

  function reveal(el) {
    var hex = el.getAttribute("data-cfemail");
    var email = decode(hex);
    if (!email || email.indexOf("@") === -1) return;
    var subject = el.getAttribute("data-mailto-subject");
    el.href = "mailto:" + email + (subject ? "?subject=" + encodeURIComponent(subject) : "");
    if (el.classList.contains("__cf_email__")) {
      el.textContent = email;
    }
  }

  document.querySelectorAll("a[data-cfemail]").forEach(reveal);
})();
