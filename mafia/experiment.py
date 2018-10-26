"""Mafia game."""

import json
import random

import dallinger as dlgr
from dallinger import db
from dallinger.models import Node, Participant, Network, timenow
from dallinger.nodes import Source
from datetime import datetime
from flask import Blueprint, Response
from faker import Faker
fake = Faker()


class MafiaExperiment(dlgr.experiments.Experiment):
    """Define the structure of the experiment."""

    def __init__(self, session):
        """Initialize the experiment."""
        super(MafiaExperiment, self).__init__(session)
        import models
        self.models = models

        self.experiment_repeats = 1
        # self.num_participants = 6
        self.num_participants = 5
        self.num_mafia = 2
        # self.num_mafia = 2
        # Note: can't do * 2.5 here, won't run even if the end result is an integer
        self.initial_recruitment_size = self.num_participants  # * 2
        self.quorum = self.num_participants
        if session:
            self.setup()
        self.known_classes["Text"] = models.Text
        self.known_classes["Vote"] = models.Vote

    def setup(self):
        """Setup the networks.

        Setup only does stuff if there are no networks, this is so it only
        runs once at the start of the experiment. It first calls the same
        function in the super (see experiments.py in dallinger). Then it adds a
        source to each network.
        """
        if not self.networks():
            super(MafiaExperiment, self).setup()
            for net in self.networks():
                Source(network=net)

    def create_network(self):
        """Create a new network by reading the configuration file."""

        mafia_network = self.models.MafiaNetwork(
            max_size=self.num_participants + 1
        )  # add a Source
        mafia_network.daytime = 'False'
        mafia_network.winner = None
        mafia_network.last_victim_name = None
        mafia_network.num_victims = 0
        return mafia_network

    def record_waiting_room_exit(self, player_id):
        end_waiting_room = datetime.now().strftime(DATETIME_FORMAT)
        self.participant.property1 = end_waiting_room

    def bonus(self, participant):
        """Give the participant a bonus for waiting."""

        DOLLARS_PER_HOUR = 5.0
        DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
        try:
            end_waiting_room = datetime.strptime(participant.property1,
                                                          DATETIME_FORMAT)
        except (TypeError, ValueError):
            # just in case something went wrong saving wait room end time
            # last_participant_creation_time = Participant.query.filter_by(
            #     ).order_by('creation_time')[-1].creation_time
            last_participant_creation_time = Participant.query.order_by('creation_time')[-1].creation_time
            end_waiting_room = last_participant_creation_time
            # end_waiting_room = participant.end_time
        t = end_waiting_room - participant.creation_time

        # keep to two decimal points otherwise doesn't work
        return round((t.total_seconds() / 3600) * DOLLARS_PER_HOUR, 2)

    def add_node_to_network(self, node, network):
        """Add node to the chain and receive transmissions."""
        network.add_node(node)
        source = network.nodes(type=Source)[0]  # find the source in the network
        source.connect(direction="to", whom=node)  # link up the source to the new node
        source.transmit(to_whom=node)  # in networks.py code, transmit info to the new node
        node.receive()  # new node receives everything

    def info_post_request(self, node, info):
        """Run when a request to create an info is complete."""

        # Proceed with normal info post request
        for agent in node.neighbors():
            node.transmit(what=info, to_whom=agent)

    def create_node(self, participant, network):
        """Create a node for a participant."""
        # Check how many mafia members there are.
        # If there aren't enough, create another:
        num_mafioso = Node.query.filter_by(type="mafioso").count()
        if num_mafioso < self.num_mafia:
            mafioso = self.models.Mafioso(network=network,
                                          participant=participant)
            mafioso.fake_name = str(fake.name())
            mafioso.alive = 'True'
            return mafioso
        else:
            bystander = self.models.Bystander(network=network,
                                              participant=participant)
            bystander.fake_name = str(fake.name())
            bystander.alive = 'True'
            return bystander


extra_routes = Blueprint(
    'extra_routes',
    __name__,
    template_folder='templates',
    static_folder='static')


@extra_routes.route("/phase/<int:node_id>/<int:switches>/<string:was_daytime>",
                    methods=["GET"])
def phase(node_id, switches, was_daytime):
    try:
        exp = MafiaExperiment(db.session)
        this_node = Node.query.filter_by(id=node_id).one()
        net = Network.query.filter_by(id=this_node.network_id).one()
        nodes = Node.query.filter_by(network_id=net.id).order_by(
            'creation_time').all()
        db.logger.exception("TEMPORARY this_node")
        db.logger.exception(this_node)
        db.logger.exception("TEMPORARY nodes")
        db.logger.exception(nodes)
        nodes_temp = Node.query.filter_by(network_id=this_node.network_id,
                                         property2='True').all()
        db.logger.exception("TEMPORARY nodes_temp")
        db.logger.exception(nodes_temp)
        node = nodes[-1]
        elapsed_time = timenow() - node.creation_time
        start_duration = 2 # this line ALSO gets set in experiment.js (hardcoded),
        # this is how long the "this person has been eliminatedTEMPORARY SWITCH BACK!" message gets displayed
        # setTimeout(function () { $("#stimulus").hide(); showExperiment(); }, 2000);
        day_round_duration = 30 # TEMPORARY SWITCH BACK 150
        night_round_duration = 30 # TEMPORARY SWITCH BACK 30
        break_duration = 10 # this line ALSO gets set in experiment.js (hardcoded),
        # this is how long the "The game will begin shortly..." message gets displayed
        # setTimeout(function () { $("#stimulus").hide(); get_transmissions(currentNodeId); }, 10000);
        daybreak_duration = day_round_duration + break_duration
        nightbreak_duration = night_round_duration + break_duration
        if elapsed_time.total_seconds() > start_duration:
            total_time = elapsed_time.total_seconds() - start_duration
        else:
            total_time = 0
        if switches % 2 == 0:
            time = night_round_duration - (
                total_time -
                switches / 2 * daybreak_duration -
                (switches / 2) * nightbreak_duration
            ) % night_round_duration
        else:
            time = day_round_duration - (
                total_time -
                (switches + 1) / 2 * nightbreak_duration -
                (((switches+1) / 2) -1) * daybreak_duration
            ) % day_round_duration
        time = int(time)
        # winner = None
        # victim_name = None
        victim_name = net.last_victim_name
        victim_type = None
        winner = net.winner
        db.logger.exception('TEMPORARY INITIAL winner')
        db.logger.exception(winner)

        db.logger.exception("TEMPORARY net.winner at beginning")
        db.logger.exception(net.winner)
        daytime = (net.daytime == 'True')

        # if the game's over, skip all code below
        # if winner is None:
        # db.logger.exception('TEMPORARY ARRIVED winner')
        # db.logger.exception(winner)
        # # If it's night but should be day, then call setup_daytime()
        # db.logger.exception('TEMPORARY variable daytime')
        # db.logger.exception(daytime)
        # if was_daytime != net.daytime:
        #     victim_name = net.last_victim_name
        #     winner = net.winner
            # nodes = Node.query.filter_by(network_id=net.id,
            #                              property2='True').all()
            # mafiosi = Node.query.filter_by(network_id=net.id,
            #                                property2='True',
            #                                type='mafioso').all()
            # victim_name = Node.query.filter_by(
            #     network_id=net.id,
            #     property2='False'
            # ).order_by('property3').all()[-1].property1
            # if len(mafiosi) >= len(nodes) - len(mafiosi):
            #     winner = 'mafia'
            # elif len(mafiosi) == 0:
            #     winner = 'bystanders'
            # db.logger.exception('TEMPORARY was_daytime != net.daytime nodeID')
            # db.logger.exception(node_id)
            # db.logger.exception('TEMPORARY was_daytime != net.daytime winner')
            # db.logger.exception(winner)
        if not daytime and (
            int(total_time -
                switches / 2 * daybreak_duration
                - (switches / 2) * nightbreak_duration
                ) == night_round_duration):
            victim_name, winner = net.setup_daytime()
            # victim_name, winner = net.setup_daytime(switches + 1)
            db.logger.exception('not daytime')
            db.logger.exception(node_id)
            db.logger.exception('not daytime')
            db.logger.exception(winner)
        # If it's day but should be night, then call setup_nighttime()
        elif daytime and (
            int(total_time -
                (switches + 1) / 2 * nightbreak_duration
                - (((switches+1) / 2) -1) * daybreak_duration
                ) == day_round_duration):
            victim_name, winner = net.setup_nighttime()
            # victim_name, winner = net.setup_nighttime(switches + 1)
            db.logger.exception('TEMPORARY after setup_nighttime nodeID')
            db.logger.exception(node_id)
            db.logger.exception('TEMPORARY after setup_nighttime winner')
            db.logger.exception(winner)

        # if game over is detected, save that knowledge
        # so it doesn't get overridden by future nodes running phase()
        # (this bit of code is absolutely necessary b/c otherwise
        #  the first node is in "daytime" and then the second node often
        #  goes to "was_daytime" and then the third node doesn't end)
        # if winner != None:
        #     net.winner = winner
        #     net.last_victim_name = victim_name


        db.logger.exception("TEMPORARY net.winner at end")
        db.logger.exception(net.winner)

        db.logger.exception('TEMPORARY nodeID')
        db.logger.exception(node_id)
        db.logger.exception('TEMPORARY winner')
        db.logger.exception(winner)
        db.logger.exception('TEMPORARY victim_name')
        db.logger.exception(victim_name)

        exp.save()

        if victim_name:
            victim_type = Node.query.filter_by(property1=victim_name).one().type
            db.logger.exception('TEMPORARY victim_type')
            db.logger.exception(victim_type)
        else:
            victim_type = None

        return Response(
            response=json.dumps({
                'time': time, 'daytime': net.daytime,
                'victim_name': victim_name, 'victim_type': victim_type, 'winner': winner
            }),
            # response=json.dumps({
            #     'time': time, 'daytime': net.daytime,
            #     'victim': [victim_name, victim_type], 'winner': winner
            # }),
            status=200,
            mimetype='application/json')
    except Exception:
        db.logger.exception('Error fetching phase')
        return Response(
            status=403,
            mimetype='application/json')


@extra_routes.route("/live_participants/<int:node_id>/<int:get_all>",
                    methods=["GET"])
def live_participants(node_id, get_all):
    try:
        exp = MafiaExperiment(db.session)
        this_node = Node.query.filter_by(id=node_id).one()
        if get_all == 1:
            nodes = Node.query.filter_by(network_id=this_node.network_id,
                                         property2='True').all()
        else:
            nodes = Node.query.filter_by(network_id=this_node.network_id,
                                         property2='True',
                                         type='mafioso').all()
        participants = []
        for node in nodes:
            if node.property1 == this_node.property1:
                participants.append(node.property1 + ' (you!)')
            else:
                participants.append(node.property1)
        random.shuffle(participants)

        exp.save()

        return Response(
            response=json.dumps({'participants': participants}),
            status=200,
            mimetype='application/json')
    except Exception:
        db.logger.exception('Error fetching live participants')
        return Response(
            status=403,
            mimetype='application/json')


class Source(Source):

    __mapper_args__ = {
        "polymorphic_identity": "source"
    }

    def _contents(self):
        """Define the contents of new Infos.
        transmit() -> _what() -> create_information() -> _contents().
        """

        # Empty
