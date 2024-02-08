import logging
import abc
from datetime import timezone, datetime
from dateutil import parser as date_parser

from .client import MondayDataError

log = logging.getLogger('eric')


class ValueType(abc.ABC):
	def __init__(self, column_id):
		self.column_id = column_id
		self._value = None

	def __str__(self):
		return str(self._value)

	def __repr__(self):
		return str(self._value)

	@abc.abstractmethod
	def column_api_data(self):
		raise NotImplementedError

	@abc.abstractmethod
	def load_column_value(self, column_data: dict):
		log.debug(f"Loading column value for {self.column_id}")


class TextValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, new_value):
		if isinstance(new_value, str):  # or any other condition you want to check
			self._value = new_value
		else:
			raise ValueError("Invalid value")

	def column_api_data(self):
		# prepare self.value for submission here
		value = str(self.value)
		return {self.column_id: value}

	def load_column_value(self, column_data: dict):
		super().load_column_value(column_data)
		try:
			value = column_data['text']
		except KeyError:
			raise InvalidColumnData(column_data, 'text')

		if value is None or value == "":
			# api has fetched a None value, indicating an emtpy column
			value = ""
		else:
			value = str(value)

		log.debug("Loaded column value: %s", value)

		self.value = value
		return self.value


class NumberValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, new_value):
		if isinstance(new_value, int):  # or any other condition you want to check
			self._value = new_value
		else:
			raise ValueError("Invalid value")

	def column_api_data(self):
		# prepare self.value for submission here
		value = int(self.value)
		return {self.column_id: value}

	def load_column_value(self, column_data: dict):
		super().load_column_value(column_data)
		try:
			value = column_data['text']
		except KeyError:
			raise InvalidColumnData(column_data, 'text')

		if value is None or value == "":
			# api has fetched a None value, indicating an emtpy column
			value = 0
		else:
			value = int(value)

		log.debug("Loaded column value: %s", value)
		self.value = value
		return self.value


class StatusValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)


	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, new_value):
		if isinstance(new_value, str):  # or any other condition you want to check
			self._value = new_value
		else:
			raise ValueError("Invalid value")

	def column_api_data(self):
		# prepare self.value for submission here
		value = str(self.value)
		return {self.column_id: {"label": value}}

	def load_column_value(self, column_data: dict):
		super().load_column_value(column_data)
		try:
			value = column_data['text']
		except KeyError:
			raise InvalidColumnData(column_data, 'text')

		if value is None or value == "":
			# api has fetched a None value, indicating an emtpy column
			value = ""
		else:
			value = str(value)

		log.debug("Loaded column value: %s", value)

		self.value = value
		return self.value


class DateValue(ValueType):
	def __init__(self, column_id: str):
		super().__init__(column_id)

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self, new_value: datetime):
		# make sure it is a datetime in UTC
		if isinstance(new_value, datetime):
			new_value = new_value.astimezone(timezone.utc)
			self._value = new_value

		elif new_value is None:
			# allow setting to None, column is cleared
			self._value = None

		else:
			raise ValueError(f"Invalid value: {new_value} ({type(new_value)})")

		log.debug("Set date value: %s", new_value)

	def column_api_data(self):
		# prepare self.value for submission here
		# desired string format: 'YYYY-MM-DD HH:MM:SS'
		value = self.value or ""
		assert isinstance(value, datetime)
		if value:
			value = value.strftime('%Y-%m-%d %H:%M:%S')
		return {self.column_id: value}

	def load_column_value(self, column_data: dict):
		super().load_column_value(column_data)
		try:
			value = column_data['text']
		except KeyError:
			raise InvalidColumnData(column_data, 'text')

		if value is None or value == "":
			# api has fetched a None value, indicating an emtpy column
			value = None
		else:
			try:
				value = date_parser.parse(value)
			except Exception as e:
				raise ValueError(f"Error parsing date value: {value}")
			assert (isinstance(value, datetime))

		log.debug("Loaded column value: %s", value)

		self.value = value
		return self.value


class InvalidColumnData(MondayDataError):

	def __init__(self, column_data: dict, key: str):
		super().__init__(f"Invalid column data, no '{key}' value in data: {column_data}")
