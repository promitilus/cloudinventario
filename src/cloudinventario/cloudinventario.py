"""CloudInventario"""
import os, sys, importlib, re, threading, logging
from pprint import pprint

from cloudinventario.storage import InventoryStorage

COLLECTOR_PREFIX = 'cloudinventario'

class CloudInventario:

   def __init__(self, config):
     self.config = config
     self.lock = threading.Lock()

   @property
   def collectors(self):
     collectors = []
     for col in self.config['collectors'].keys():
        if self.config['collectors'][col].get("disabled") != True:
          collectors.append(col)
     return collectors

   @ property
   def expiredCollectors(self):
     # TODO
     pass

   def collectorConfig(self, collector):
     return self.config['collectors'][collector]

   def loadCollector(self, collector, options = None):
     mod_cfg = self.collectorConfig(collector)

     mod_name = mod_cfg['module']
     mod_name = re.sub(r'[/.]', '_', mod_name) # basic safety, should throw error
     mod_name = re.sub(r'_', '__', mod_name)
     mod_name = re.sub(r'-', '_', mod_name)

     mod = importlib.import_module(COLLECTOR_PREFIX + '_' + mod_name + '.collector')
     mod_instance = mod.setup(collector, mod_cfg['config'], mod_cfg.get('default', {}), options or {})
     return mod_instance

   def collect(self, collector, options = None):
     # workaround for buggy libs
     wd = os.getcwd()
     os.chdir("/tmp")

     inventory = None
     try:
       instance = self.loadCollector(collector, options)

       if instance.login():
         inventory = instance.fetch()
         instance.logout()
     except Exception as e:
       logging.error("Exception while processing collector={}".format(collector))
       raise
     finally:
       os.chdir(wd)
     return inventory

   def store(self, inventory):
     store_config = self.config["storage"]

     with self.lock:
       store = InventoryStorage(store_config)

       store.connect()
       store.save(inventory)
       store.disconnect()

     return True

   def cleanup(self, days):
     store_config = self.config["storage"]
     store = InventoryStorage(store_config)

     store.connect()
     store.cleanup(days)
     store.disconnect()
