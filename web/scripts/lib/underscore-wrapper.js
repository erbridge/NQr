/* global define */

define(function(require) {
    "use strict";

    var _ = require("underscore-base");

    _.templateSettings.trim = /\n\s*/g;

    return _;
});
