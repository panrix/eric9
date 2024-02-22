from ..api.items import BaseItemType, BaseCacheableItem
from ..api import columns, get_api_items
from ..api.exceptions import MondayDataError
from ....utilities import notify_admins_of_error
from .repair_phases import RepairPhaseModel


class ProductItem(BaseCacheableItem):
	BOARD_ID = 2477699024

	def __init__(self, item_id=None, api_data: dict | None = None, search=False):
		self.device_connect = columns.ConnectBoards("link_to_devices6")
		self.parts_connect = columns.ConnectBoards("connect_boards8")
		self.phase_model_connect = columns.ConnectBoards("board_relation4")

		self.price = columns.NumberValue("numbers")

		self.required_minutes = columns.NumberValue("numbers7")
		self.woo_commerce_product_id = columns.TextValue("text3")

		self.product_type = columns.StatusValue("status3")

		self._device_id = None

		super().__init__(item_id, api_data, search)

	@classmethod
	def fetch_all(cls, index_items=False):
		results = super().fetch_all("product:")
		filtered = []
		for item in results:
			if not index_items and item.product_type.value == 'Index':
				continue
			filtered.append(item)
		return filtered

	@classmethod
	def get(cls, product_ids):
		results = []
		failed = []
		try:
			for _ in product_ids:
				try:
					results.append(cls(_).load_from_cache())
				except Exception as e:
					notify_admins_of_error(f"Error fetching product{_} from cache: {str(e)}")
					failed.append(_)
			if failed:
				prod_data = get_api_items(failed)
				results.append([cls(_).load_from_api(prod_data[_]) for _ in prod_data])
		except Exception as e:
			notify_admins_of_error(f"Error fetching products {product_ids}: {str(e)}")

	def cache_key(self):
		return f"product:{self.id}"

	def load_from_cache(self, cache_data=None):
		if cache_data is None:
			cache_data = self.fetch_cache_data()
		self.price.value = int(cache_data['price'])
		self.required_minutes.value = int(cache_data['required_minutes'])
		self.name = cache_data['name']
		self._device_id = cache_data['device_id']
		self.id = cache_data['id']
		return self

	def prepare_cache_data(self):
		data = {
			"price": self.price.value,
			"required_minutes": self.required_minutes.value,
			"name": self.name,
			"device_id": self.device_id,
			"id": self.id
		}

		if not data['device_id']:
			notify_admins_of_error(f"Device ID not set for product {self.id}")

		return data

	@property
	def device_id(self):
		if not self._device_id:
			if self.device_connect.value:
				self._device_id = self.device_connect.value[0]
			else:
				notify_admins_of_error(f"{str(self)} has no device connection")
		return self._device_id

	def get_phase_model(self):
		if not self.phase_model_connect.value:
			# use default phase model
			pm = RepairPhaseModel(6106627585)
		else:
			pm = RepairPhaseModel(self.phase_model_connect.value[0])
		return pm.load_from_api()
