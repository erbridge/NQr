/* global define */

define(function(require) {
    "use strict";

    var Backbone = require("backbone");
    var _        = require("underscore");

    var player = require("player");

    var Control = Backbone.View.extend({
        className: "control",

        initialize: function(args) {
            var self = this;
            _.each(_.keys(args), function(arg) {
                self[arg] = args[arg];
            });
        },

        render: function() {
            this.$el.html(player.buttonMap[this.type]);
            this.$el.click(player[this.type]);

            return this;
        }
    });

    var PlayerControls = Backbone.View.extend({
        className: "player-controls",

        render: function() {
            var self = this;
            _.each(_.keys(player.buttonMap), function(methodName) {
                self.$el.append(new Control({
                    type: methodName
                }).render().$el);
            });

            return this;
        }
    });

    return PlayerControls;
});
