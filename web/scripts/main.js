/* global require */

// FIXME: Use minified versions when not in development mode?
require.config({
    baseUrl: "scripts",
    paths: {
        backbone: "lib/backbone",
        "dom-ready": "lib/require/dom-ready",
        jquery: "lib/jquery",
        text: "lib/require/text",
        "underscore-base": "lib/underscore",
        underscore: "lib/underscore-wrapper"
    },
    shim: {
        backbone: {
            deps: ["underscore", "jquery"],
            exports: "Backbone"
        },
        "underscore-base": {
            exports: "_"
        }
    }
});

require([
        "dom-ready!",
        "jquery",
        "underscore",
        "player-controls"
    ],
    function(
        doc,
        $,
        _,
        PlayerControls) {

    "use strict";

    $("body").html(new PlayerControls().render().el);
});
