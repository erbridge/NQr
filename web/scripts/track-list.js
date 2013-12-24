/* global define */

define(function(require) {
    "use strict";

    var Backbone = require("backbone");
    var $        = require("jquery");
    var _        = require("underscore");

    var Entry = Backbone.View.extend({
        tagName:   "tr",
        className: "entry",
        template:  _.template(require("text!templates/track-list-entry.html")),

        initialize: function(args) {
            this.track = args.track;
            this.$el.attr("id", this.track.trackID);
        },

        render: function() {
            this.$el.html(this.template({
                track: this.track
            }));

            this.$(".score").click(function() {
                var $dropdown = $("<select>");
                for (var i = 10; i > -11; i--) {
                    $dropdown.append($("<option>").html(i));
                }
                $(this).html($dropdown).change(function() {
                    var score = parseInt($(":selected", this).text());
                    $.post("changeScore", JSON.stringify({
                        score: score
                    }));
                    $(this).html(score).unbind("change");
                });
            });

            return this;
        }
    });

    var TrackList = Backbone.View.extend({
        tagName:   "table",
        className: "track-list",
        template:  _.template(require("text!templates/track-list-header.html")),

        render: function() {
            this.$el.html(this.template());

            this.update();
            setInterval(this.update, 1000);

            return this;
        },

        update: function() {
            var self = this;
            $.getJSON("trackInfo", function(track) {
                var firstTrack = self.$(".entry:first");
                if (firstTrack.attr("id") != track.trackID) {
                    self.$(".header").after(new Entry({
                        track: track
                    }).render().el);
                }
            });
        }
    });

    return TrackList;
});
