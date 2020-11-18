#!/usr/bin/env python3

import time

from kazoo import client as kazooclient
from keystoneauth1 import loading
from keystoneauth1 import session
from neutronclient.neutron import client as neutronclient
from oslo_config import cfg
from oslo_log import log
import oslo_messaging


CONF = cfg.CONF
LOG = log.getLogger('mido-fixer')
SRV_CREDS_GRP = 'service_credentials'


class NotificationHandler(object):

    def __init__(self, zk):
        self.dry_run = False
        self._session = None
        self._neutron = None
        self.zk = zk

    @property
    def session(self):
        if self._session is None:
            loading.register_auth_conf_options(CONF, SRV_CREDS_GRP)
            auth = loading.load_auth_from_conf_options(CONF, SRV_CREDS_GRP)
            self._session = session.Session(auth=auth)
        return self._session

    @property
    def neutron(self):
        if self._neutron is None:
            self._neutron = neutronclient.Client(
                '2.0', session=self.session)
        return self._neutron

    def mido_fix(self, port_id):
        try:
            port = self.neutron.show_port(port_id)['port']
        except Exception:
            return
        net_id = port['network_id']
        mac_address = port['mac_address']
        ip_addresses = [ip['ip_address'] for ip in port['fixed_ips']]
        LOG.debug("Network ID %s", net_id)
        LOG.debug("mac_address %s", mac_address)
        LOG.debug("ip_addresses %s", ip_addresses)
        base_path = "/midonet/zoom/0/tables/Network/%s/ip4_mac_table" % net_id
        try:
            arp_table = self.zk.get_children(base_path)
        except Exception:
            LOG.debug("No path, skipping")
            return
        for address in ip_addresses:
            for entry in arp_table:
                if entry.startswith("%s," % address) and not entry.startswith(
                        "%s,%s" % (address, mac_address)):
                    LOG.warn("Found duplicate at %s", entry)
                    path = '%s/%s' % (base_path, entry)
                    LOG.info("Deleting path %s", path)
                    self.zk.delete(path)

    def sample(self, ctxt, publisher_id, event_type, payload, metadata):
        try:
            traits = {d[0]: d[2] for d in payload[0]['traits']}
            LOG.debug('Processing notification for %s', traits['resource_id'])
            port_id = traits['resource_id']
            # We need to wait for the port to exist via the API, sometimes
            # we're too quick
            time.sleep(2)
            self.mido_fix(port_id)
        except Exception:
            LOG.exception('Unable to handle notification: %s', payload)

        return oslo_messaging.NotificationResult.HANDLED


class Agent(object):

    def __init__(self):
        self._zk = None
        transport = oslo_messaging.get_notification_transport(CONF)
        targets = [
            oslo_messaging.Target(exchange='ceilometer',
                                  topic='event')
        ]
        endpoints = [NotificationHandler(self.zk)]
        server = oslo_messaging.get_notification_listener(
            transport, targets, endpoints, executor='threading')
        self.server = server

    @property
    def zk(self):
        if self._zk is None:
            self._zk = kazooclient.KazooClient(CONF.zookeeper.host)
            self._zk.start()
        return self._zk

    def run(self):
        try:
            self.server.start()
            LOG.info('Waiting for notifications')
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            LOG.info('Stopping agent')

        self.zk.stop()
        self.server.stop()
        self.server.wait()


def zookeeper_opts():
    zookeeper_group = cfg.OptGroup('zookeeper')
    zookeeper_opts = [
        cfg.StrOpt('host', help='Zookeeper Host'),
    ]

    CONF.register_group(zookeeper_group)
    CONF.register_opts(zookeeper_opts, group=zookeeper_group)


class main(object):
    log.register_options(CONF)
    log.set_defaults(default_log_levels=log.get_default_log_levels())
    log.setup(CONF, 'mido-fixer')

    zookeeper_opts()

    CONF([],
         project='mido-fixer',
         default_config_files=['/etc/mido-fixer/mido-fixer.conf'])

    LOG.info('Starting agent')
    agent = Agent()
    agent.run()


if __name__ == '__main__':
    main()
