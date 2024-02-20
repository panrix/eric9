import logging
import abc
import json

import redis.utils

from .columns import ValueType, EditingNotAllowed
from .client import conn
from .exceptions import MondayDataError, MondayAPIError
from ....cache import get_redis_connection, CacheMiss
from .client import get_api_items, conn
from ....utilities import notify_admins_of_error

log = logging.getLogger('eric')


class BaseItemType:
	BOARD_ID = None

	@classmethod
	def fetch_all(cls):
		log.debug(f"Fetching all items for {cls.__name__}")
		query_results = conn.boards.fetch_items_by_board_id(cls.BOARD_ID)['data']['boards'][0]['items_page']
		cursor = query_results['cursor']
		items = [cls(item['id'], item) for item in query_results['items']]
		while cursor:
			query_results = conn.boards.fetch_items_by_board_id(
				cls.BOARD_ID,
				cursor=cursor
			)['data']['boards'][0]['items_page']
			cursor = query_results['cursor']
			items += [cls(item['id'], item) for item in query_results['items']]
			log.debug(f"Cursor: {cursor}, {len(query_results['items'])} items fetched")
			if not cursor:
				break
		return items

	def __init__(self, item_id=None, api_data: dict = None, search=False):
		self.id = item_id
		self.name = None

		self.staged_changes = {}

		self._api_data = None
		self._column_data = None
		if not search:
			self.load_data(api_data)

	def __str__(self):
		if self.name:
			return f"{self.__class__.__name__}({self.id}): {self.name}"
		else:
			return f"{self.__class__.__name__}({self.id})"

	def __setattr__(self, name, value):
		# Check if the attribute being assigned is an instance of ValueType
		if getattr(self, name, None) and isinstance(getattr(self, name), ValueType):
			getattr(self, name).value = value
			self.staged_changes.update(getattr(self, name).column_api_data())
		else:
			# Call the parent class's __setattr__ method
			super().__setattr__(name, value)

	def load_data(self, api_data=None):
		# load the item data from the API
		if api_data:
			self.load_from_api(api_data)
		elif not api_data and self.id:
			self.load_from_api()

	def load_from_api(self, api_data=None):
		# load the item data from the API
		log.debug(f"Loading item data for {self.__class__.__name__} {self.id}")
		if not api_data and self.id:
			log.debug("No Data provided, fetching...")
			api_data = get_api_items([self.id])[0]
		elif not api_data and not self.id:
			raise IncompleteItemError(self, "Item ID not set (not created)")

		if str(self.id) != str(api_data['id']):
			raise MondayDataError(f"Item ID {self.id} does not match ID in API data: {api_data['id']}")

		assert 'id' in api_data
		assert 'column_values' in api_data
		assert 'name' in api_data

		self._api_data = api_data
		self._column_data = api_data['column_values']

		self.id = api_data['id']
		self.name = api_data['name']

		for att in dir(self):
			instance_property = getattr(self, att)
			if isinstance(instance_property, ValueType):
				desired_column_id = instance_property.column_id
				try:
					column_data = [col for col in self._column_data if col['id'] == desired_column_id][0]
				except IndexError:
					raise ValueError(f"Column with ID {desired_column_id} not found in item data")

				instance_property.load_column_value(column_data)

		self.staged_changes = {}
		return self

	def commit(self, name=None):
		# commit changes to the API
		if not self.id and not name:
			raise IncompleteItemError(self, "Item ID (of an existing item) or name param must be provided")
		elif not self.id and name:
			self.create(name)
		try:
			return conn.items.change_multiple_column_values(
				board_id=self.BOARD_ID,
				item_id=self.id,
				column_values=self.staged_changes
			)
		except Exception as e:
			raise MondayAPIError(f"Error calling monday API: {e}")

	def create(self, name):
		# create a new item in the API
		try:
			new_item = conn.items.create_item(
				board_id=self.BOARD_ID,
				group_id="",
				item_name=name,
				column_values=self.staged_changes
			)
			self.id = new_item['data']['create_item']['id']
			return self
		except Exception as e:
			raise MondayAPIError(f"Error calling monday API: {e}")

	def add_update(self, body, thread_id=None):

		if self.id is None:
			raise IncompleteItemError(self, "Item ID not set (not created)")
		else:
			return conn.updates.create_update(
				item_id=self.id,
				update_value=body,
				thread_id=str(thread_id) if thread_id else None
			)

	def search_board_for_items(self, attribute, value):

		att = getattr(self, attribute)
		if not att:
			raise AttributeError(f"{attribute} is not a valid attribute of {self.__class__.__name__}")

		assert isinstance(att, ValueType), f"{attribute} cannot be used to search for items"

		return att.search_for_board_items(self.BOARD_ID, value)


class BaseCacheableItem(BaseItemType):

	def __init__(self, item_id=None, api_data: dict = None, search=False):
		super().__init__(item_id, api_data, search)

	def load_data(self, api_data=None):
		# load the item data from the cache
		try:
			if api_data:
				self.load_from_api(api_data)
			else:
				self.load_from_cache()
		except CacheMiss:
			notify_admins_of_error(f"Cache miss for {str(self)} {self.id}")
			self.load_from_api()

	@abc.abstractmethod
	def cache_key(self):
		# load the item data from the cache
		raise NotImplementedError

	def fetch_cache_data(self):
		cache_data = get_redis_connection().get(self.cache_key())
		if not cache_data:
			raise CacheMiss(self.cache_key(), cache_data)
		cache_data = cache_data.decode('utf-8')
		cache_data = json.loads(cache_data)
		return cache_data

	@abc.abstractmethod
	def prepare_cache_data(self):
		raise NotImplementedError

	def save_to_cache(self, pipe: redis.utils.pipeline = None):
		cache_data = self.prepare_cache_data()
		if pipe:
			pipe.set(self.cache_key(), json.dumps(cache_data))
		else:
			get_redis_connection().set(self.cache_key(), json.dumps(cache_data))
		return cache_data

	@abc.abstractmethod
	def load_from_cache(self):
		raise NotImplementedError


class IncompleteItemError(MondayDataError):
	"""Error raised when item attributes that have not been fetched or created are accessed"""

	def __init__(self, item, error_message):
		self.item = item
		self.error_message = error_message

	def __str__(self):
		return f"IncompleteItemError({str(self.item)}): {self.error_message}"
