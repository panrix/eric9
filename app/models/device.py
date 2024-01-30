import logging

import moncli
from moncli.models import MondayModel
from moncli import types as cols

from .base import BaseEricCacheModel
from .product import ProductModel
from ..services import monday
from ..cache import get_redis_connection

log = logging.getLogger('eric')


class _BaseDeviceModel(MondayModel):
	product_ids = cols.ItemLinkType(id='connect_boards5')
	legacy_eric_device_id = cols.TextType(id='text')
	product_index_connect = cols.ItemLinkType(id='connect_boards4')
	device_type = cols.StatusType(id='status9')


class DeviceModel(BaseEricCacheModel):

	MONCLI_MODEL = _BaseDeviceModel

	@classmethod
	def query_all(cls):
		return get_redis_connection().keys("device:*")

	def __init__(self, device_id, moncli_item: moncli.en.Item = None):
		if moncli_item:
			super().__init__(device_id, moncli_item)
		else:
			super().__init__(device_id)

		self._product_ids = None
		self._products = None

	def __str__(self):
		return f"Device({self.id})"

	def prepare_cache_data(self):
		return {
			"name": self.name,
			"device_id": str(self.id),
			"product_ids": self.product_ids,
			"device_type": self.model.device_type
		}

	@property
	def cache_key(self):
		return f"device:{self.id}"

	@property
	def product_ids(self):
		if self._product_ids is None:
			ids = [str(item) for item in self.model.product_ids]
			self._product_ids = ids
		return self._product_ids

	@property
	def products(self):
		if self._products is None:
			items = monday.get_items(self.product_ids)
			self._products = [ProductModel(_.id, _) for _ in items]
		return self._products

	def connect_to_product_group(self):
		if not self.model.legacy_eric_device_id or self.model.legacy_eric_device_id == "new_group77067":  # index Group ID:
			log.debug(f"Correcting legacy ID for {self.model.name}: {self.model.legacy_eric_device_id}")
			if self.products:
				prod = self.products[0]
				device_group_id = prod.model.item.get_group().id
				if device_group_id == "new_group77067":  # index Group ID
					prod = self.products[1]
					device_group_id = prod.model.item.get_group().id
				self.model.legacy_eric_device_id = device_group_id
				for p in self.products:
					if not p.model.legacy_eric_device_id or p.model.legacy_eric_device_id == "new_group77067":  # index Group ID
						p.model.legacy_eric_device_id = device_group_id
						p.model.save()
				self.model.save()
		else:
			return True
