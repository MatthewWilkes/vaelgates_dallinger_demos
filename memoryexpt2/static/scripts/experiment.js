/*global $, dallinger, pubsub */

(function ($, dallinger, pubsub) {

    var currentNodeId;
    var currentPlayerId;
    // var FILLER_TASK_DURATION_MSECS = 30000
    // var WORD_DISPLAY_DURATION_MSECS = 2000
    // var FETCH_TRANSMISSION_FREQUENCY_MSECS = 100
    var FILLER_TASK_DURATION_MSECS = 3000;
    var WORD_DISPLAY_DURATION_MSECS = 1000;
    var FETCH_TRANSMISSION_FREQUENCY_MSECS = 3000;
    var go = {
        questionnaire: function () {
            dallinger.allowExit();
            dallinger.goToPage("questionnaire");
        }
    };
    var uniqueWords = {
        _words: [],
        add: function (word) {
            word = word.toLowerCase().trim();
            // No empty words
            if (word.length === 0) {
                return false;
            }
            // No words with spaces
            if (word.indexOf(" ") !== -1) {
                return false;
            }
            // No non-unique words
            if (this._words.indexOf(word) !== -1) {
                return false;
            }

            this._words.push(word);
            return word;
        }
    };

    var WordSubmission = (function () {

        /**
         * Tracks turns and handles canditate word submissions.
         */
        var WordSubmission = function (settings) {
            if (!(this instanceof WordSubmission)) {
                return new WordSubmission(settings);
            }
            this.egoID = settings.egoID;
            this.socket = settings.socket;
            this._enabled = false;
            this.$button = $("#send-message");
            this.$input = $("#reproduction");
            this._bindEvents();
            this.socket.subscribe(this.changeOfTurn, "change_of_turn", this);
        };

        WordSubmission.prototype.checkAndSendWord = function () {
            if (! this._enabled) {
                return;
            }
            var self = this;
            var newWord = uniqueWords.add(self.$input.val());
            if (! newWord) {
                return;
            }
            $("#reply").append("<p style='color: #1693A5;'>" + newWord + "</p>");
            self.$input.val("");
            self.$input.focus();

            dallinger.createInfo(
                currentNodeId,
                {contents: newWord, info_type: "Info"}
            ).done(function(resp) {
                self.$button.removeClass("disabled");
                self.$button.html("Send");
            });
        };

        WordSubmission.prototype.changeOfTurn = function (msg) {
            currentPlayerId = msg.player_id;
            if (currentPlayerId === this.egoID) {
                console.log("It's our turn.");
                this._enable();
            } else {
                console.log("It's not our turn.");
                this._disable();
            }
        };

        WordSubmission.prototype._bindEvents = function () {
            var self = this;
            $(document).keypress(function(e) {
                if (e.which === 13) {
                    self.$button.click();
                    return false;
                }
            });
            self.$button.click(function() {
                self.checkAndSendWord();
            });
        };

        WordSubmission.prototype._disable = function () {
            this._enabled = false;
            this.$button.attr("disabled", true);
        };

        WordSubmission.prototype._enable = function () {
            this._enabled = true;
            this.$button.attr("disabled", false);
        };

        return WordSubmission;
    }());

    $(document).ready(function() {

        var egoParticipantId = dallinger.getUrlParameter("participant_id"),
            wordSubmission,
            socket;

        // Leave the chatroom.
        $("#leave-chat").click(function() {
            go.questionnaire();
        });
        console.log("Starting socket with participantID " + egoParticipantId);
        socket = startSocket(egoParticipantId);
        wordSubmission = new WordSubmission(
            {egoID: egoParticipantId, socket: socket}
        );
        startPlayer();
    });

    function startSocket(playerID) {
        var socketSettings = {
            "endpoint": "chat",
            "broadcast": "memoryexpt2",
            "control": "memoryexpt2_ctrl",
        };
        var socket = pubsub.Socket(socketSettings);
        socket.open().done(
            function () {
                var data = {
                    type: "connect",
                    player_id: playerID
                };
                socket.send(data);
            }
        );
        return socket;
    }
    // Create the agent.
    function startPlayer() {
        dallinger.createAgent().done(function (resp) {
            currentNodeId = resp.node.id;
            getWordList();
        }).fail(function (rejection) {
            if (rejection.status === 403) {
                return;
            } else {
                dallinger.error(rejection);
            }
        });
    }


    function getWordList() {
        dallinger.get(
            "/node/" + currentNodeId + "/received_infos"
        ).done(function(resp) {
            var wordList = JSON.parse(resp.infos[0].contents);
            showWordList(wordList);
        });
    }

    function showWordList(wl) {
        if (wl.length === 0) {
            // Show filler task.
            showFillerTask();
        } else {
            // Show the next word.
            $("#wordlist").html(wl.pop());
            setTimeout(
                function() {
                    showWordList(wl);
                },
                WORD_DISPLAY_DURATION_MSECS
            );
        }
    }

    function showFillerTask() {
        var filler_answers = [];
        $("#stimulus").hide();
        $("#fillertask-form").show();

        setTimeout(
            function() {
                // store results of filler tasks in array
                $("#fillertask-form input").each(function( i, item ) {
                    filler_answers.push("{" + item.name + ": " + item.value + "}");
                });
                // stores all filler answers in the contents column of info table
                dallinger.createInfo(
                    currentNodeId,
                    {contents: filler_answers.join(", "), info_type: "Info"}
                ).done(function(resp) {
                    showExperiment();
                });
            },
            FILLER_TASK_DURATION_MSECS
        );
    }

    function showExperiment() {
        $("#fillertask-form").hide();
        $("#response-form").show();
        $("#send-message").removeClass("disabled");
        $("#send-message").html("Send");
        $("#reproduction").focus();
        getTransmissions();
    }

    function getTransmissions() {
        dallinger.getTransmissions(
            currentNodeId,
            {status: "pending"}
        ).done(function(resp) {
            console.log("Got transmissions...");
            var transmissions = resp.transmissions;
            for (var i = transmissions.length - 1; i >= 0; i--) {
                displayInfo(currentNodeId, transmissions[i].info_id);
            }
            setTimeout(function () {
                getTransmissions(currentNodeId);
            },
            FETCH_TRANSMISSION_FREQUENCY_MSECS);
        });
    }

    function displayInfo(nodeId, infoId) {
        dallinger.getInfo(
            nodeId, infoId
        ).done(function(resp) {
            var newWord = uniqueWords.add(resp.info.contents);
            if (newWord) {
                $("#reply").append("<p>" + newWord + "</p>");
            }
        });
    }

}($, dallinger, pubsub));
