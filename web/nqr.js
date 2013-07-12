function pause(e) {
	e.preventDefault();
	$.get("pause");
}

function play(e) {
	e.preventDefault();
	$.get("play");
}

function stop(e) {
	e.preventDefault();
	$.get("stop");
}

function next(e) {
	e.preventDefault();
	$.get("next");
}

function prev(e) {
	e.preventDefault();
	$.get("prev");
}

function buildQueueItem(name, valueStr) {
	return "<td id=\"" + name + "\">" + valueStr + "</td>";
}

function buildQueueEntry(queueHeadID, entryIDName, track) {
	$(queueHeadID).after("<tr id=\"" + entryIDName + "\">"
			+ buildQueueItem("artist", track.artist)
			+ buildQueueItem("title", track.title)
			+ buildQueueItem("score", track.score)
			+ buildQueueItem("playedAt", track.playedAt)
			+ buildQueueItem("lastPlayed", track.lastPlayed)
			+ buildQueueItem("weight", track.weight)
			+ "</tr>");
	$("#score:first").click(function() {
	    htmlStr = "<select>";
	    for (i = 10 ; i > -11 ; --i) {
	    	htmlStr += "<option>" + i + "</option>";
	    }
	    htmlStr += "</select>";
	    $(this).html(htmlStr).change(function() {
	    	alert("changed to " + $(":selected", this).text());
	    });
	});
}