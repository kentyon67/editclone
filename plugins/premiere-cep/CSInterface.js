/**
 * CSInterface.js — Minimal Adobe CEP bridge
 * Wraps the internal __adobe_cep__ object exposed by the Chromium Embedded Framework.
 * Only the methods used by EditClone are implemented here.
 */

/* global __adobe_cep__ */

(function () {
  "use strict";

  function CSInterface() {
    this.hostEnvironment = (function () {
      try {
        return JSON.parse(window.__adobe_cep__.getHostEnvironment());
      } catch (e) {
        return { appName: "PPRO", appVersion: "0.0" };
      }
    })();
  }

  /**
   * Evaluate an ExtendScript expression in the host application.
   * @param {string} script
   * @param {function} [callback] - called with (result: string)
   */
  CSInterface.prototype.evalScript = function (script, callback) {
    if (typeof __adobe_cep__ !== "undefined") {
      __adobe_cep__.evalScript(script, function (res) {
        if (typeof callback === "function") callback(res);
      });
    } else {
      if (typeof callback === "function") callback("error:CSInterface_unavailable");
    }
  };

  /**
   * Open a URL in the system default browser.
   * @param {string} url
   */
  CSInterface.prototype.openURLInDefaultBrowser = function (url) {
    if (typeof __adobe_cep__ !== "undefined") {
      __adobe_cep__.openURLInDefaultBrowser(url);
    } else {
      window.open(url, "_blank");
    }
  };

  /**
   * Register a listener for host-side events.
   * @param {string} type
   * @param {function} listener
   */
  CSInterface.prototype.addEventListener = function (type, listener) {
    if (typeof __adobe_cep__ !== "undefined") {
      __adobe_cep__.addEventListener(type, listener, null);
    }
  };

  /**
   * Remove a previously registered event listener.
   * @param {string} type
   * @param {function} listener
   */
  CSInterface.prototype.removeEventListener = function (type, listener) {
    if (typeof __adobe_cep__ !== "undefined") {
      __adobe_cep__.removeEventListener(type, listener, null);
    }
  };

  /**
   * Dispatch a CEP event to the host.
   * @param {string} type
   * @param {*} [data]
   */
  CSInterface.prototype.dispatchEvent = function (type, data) {
    if (typeof __adobe_cep__ !== "undefined") {
      var event = { type: type, data: data };
      __adobe_cep__.dispatchEvent(JSON.stringify(event));
    }
  };

  /**
   * Get the path to the CEP extension root directory.
   * @returns {string}
   */
  CSInterface.prototype.getSystemPath = function (pathType) {
    if (typeof __adobe_cep__ !== "undefined") {
      var paths = JSON.parse(__adobe_cep__.getSystemPath(pathType || "extension"));
      return paths;
    }
    return "";
  };

  window.CSInterface = CSInterface;
})();
