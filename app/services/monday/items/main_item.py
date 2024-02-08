from ..api import items, columns


class MainItem(items.BaseItemType):
	BOARD_ID = 349212843

	text = columns.TextValue('text69')
	number = columns.NumberValue('dup__of_quote_total')
	status = columns.StatusValue('status_161')
	date = columns.DateValue('date6')
	url_link = columns.LinkURLValue('link1')
	product_connect = columns.ConnectBoards('board_relation')
	long_text = columns.LongTextValue("long_text5")