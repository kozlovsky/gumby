import time
from binascii import unhexlify

from ipv8.dht import DHTError

from tribler_core.components.ipv8.ipv8_component import Ipv8Component

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import ExperimentModule


class DHTModule(ExperimentModule):
    """
    This module contains code to manage experiments with the DHT community.
    """

    def __init__(self, experiment):
        super(DHTModule, self).__init__(experiment)
        self.start_time = 0

    def on_id_received(self):
        super(DHTModule, self).on_id_received()
        tribler_config = getattr(self.experiment, 'tribler_config', None)
        assert tribler_config
        tribler_config.dht.enabled = True
        self.tribler_config = tribler_config
        self.start_time = time.time()

    @property
    def overlay(self):
        ipv8_component = Ipv8Component.instance()
        assert ipv8_component
        return ipv8_component.dht_discovery_community

    @experiment_callback
    def introduce_peers_dht(self):
        for peer_id in self.all_vars.keys():
            if int(peer_id) != self.my_id:
                self.overlay.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))

    @experiment_callback
    async def store(self, key, value):
        await self.log_timing(self.overlay.store_value(unhexlify(key), value.encode('utf-8')), 'store')

    @experiment_callback
    async def find(self, key):
        await self.log_timing(self.overlay.find_values(unhexlify(key)), 'find')

    @experiment_callback
    async def do_dht_announce(self):
        try:
            nodes = await self.overlay.store_peer()
        except Exception as e:
            self._logger.error("Error when storing peer: %s", e)
            return

        if nodes is not None:
            self._logger.info("Stored this peer on %d nodes", len(nodes))

    async def log_timing(self, coro, op):
        ts = time.time() - self.start_time
        try:
            await coro
            self.write_to_log('dht.log', '%d %s %.3f\n', ts, op, time.time() - self.start_time - ts)
        except DHTError:
            self.write_to_log('dht.log', '%d %s -1\n', ts, op)

    def write_to_log(self, fn, string, *values):
        with open(fn, 'a') as fp:
            fp.write(string % values)
