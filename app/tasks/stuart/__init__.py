import datetime
import json

from ...services import monday, stuart
from ...utilities import notify_admins_of_error


def book_collection(main_id):
	"""Book a collection for a main item"""
	main_item = monday.items.MainItem(main_id).load_from_api()
	try:
		job_data = stuart.helpers.generate_job_data(main_item, 'incoming')
	except Exception as e:
		main_item.add_update(f"Could not generate job data: {e}", main_item.error_thread_id)
		main_item.be_courier_collection = 'Error'
		main_item.commit()
		return main_item
	try:
		response = stuart.client.create_job(job_data)
		response = response.json()
	except Exception as e:
		main_item.add_update(f"Could not create job: {e}", main_item.error_thread_id)
		main_item.be_courier_collection = 'Error'
		main_item.commit()
		return main_item

	log_job_data(job_data, response, main_item)
	return response


def log_job_data(booking_data, stuart_response, main_item):
	"""Log the job data"""

	try:
		log_item = monday.items.misc.CourierDataDumpItem()

		log_item.job_id = str(stuart_response['id'])
		# if main_item.booking_date.value:
		# 	log_item.booking_time = main_item.booking_date.value
		# else:
		# 	log_item.booking_time = datetime.datetime.now()

		log_item.cost_inc_vat = stuart_response['pricing']['price_tax_included']
		log_item.cost_ex_vat = stuart_response['pricing']['price_tax_excluded']
		log_item.vat = stuart_response['pricing']['tax_amount']

		log_item.collection_postcode = stuart_response['deliveries'][0]['pickup']['address']['postcode']
		log_item.delivery_postcode = stuart_response['deliveries'][0]['dropoff']['address']['postcode']
		log_item.distance = stuart_response['distance']
		log_item.tracking_url = ["Tracking", stuart_response['deliveries'][0]['tracking_url']]
		log_item.main_item_id = str(main_item.id)

		log_item.create(main_item.name)

		log_item.add_update(json.dumps(booking_data, indent=4))

		return log_item

	except Exception as e:
		notify_admins_of_error(e)
		raise e
