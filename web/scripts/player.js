/* global define */

define(function(require) {
    "use strict";

    var $ = require("jquery");
    var _ = require("underscore");

    var player = {
        buttonMap: {
            play:  "Play",
            pause: "Pause",
            stop:  "Stop",
            next:  "Next",
            prev:  "Prev"
        }
    };

    _.each(_.keys(player.buttonMap), function(methodName) {
        player[methodName] = function(e) {
            e.preventDefault();
            $.get(methodName);
        };
    });

    return player;
});
