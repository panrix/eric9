import logging
from flask import Blueprint, jsonify, request
import json

from ...cache.rq import q_low
from ...services import monday
from ...tasks.monday import web_bookings
from ...tasks import sync_platform
import config

conf = config.get_config()

log = logging.getLogger('eric')

monday_misc_bp = Blueprint('monday_misc', __name__, url_prefix='/monday/misc')


@monday_misc_bp.route('/enquiry', methods=['POST'])
@monday.monday_challenge
def push_web_enquiry_to_zendesk():
	log.debug('Handling Main Board Main Status Change')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	if conf.CONFIG in ("DEVELOPMENT", "TESTING"):
		web_bookings.push_web_enquiry_to_zendesk(data['pulseId'])
	else:
		q_low.enqueue(
			web_bookings.push_web_enquiry_to_zendesk,
			data['pulseId']
		)

	return jsonify({'message': 'OK'}), 200


@monday_misc_bp.route('/info-sync', methods=['POST'])
@monday.monday_challenge
def sync_item_with_external_services():
	log.debug('Handling Main Board Data Change')
	webhook = request.get_data()
	data = webhook.decode('utf-8')
	data = json.loads(data)['event']

	if conf.CONFIG in ("DEVELOPMENT", "TESTING"):
		sync_platform.sync_to_external_corporate_boards(data['pulseId'])
	else:
		q_low.enqueue(
			sync_platform.sync_to_external_corporate_boards,
			data['pulseId']
		)

	return jsonify({'message': 'OK'}), 200

@monday_misc_bp.route('/add-woocommerce-order-to-monday', methods=['POST'])
def process_woo_order():
	log.debug('Processing WooCommerce Order')
	try:
		webhook = request.get_data()
		print(webhook)
		data = webhook.decode('utf-8')
		print(data)
		data = json.loads(data)
		print(data)

		item = monday.items.misc.WebBookingItem(data)
		item.woo_commerce_order_id = int(data['id'])
		item.create(data['event']['body']['first_name']['billing'])
	except Exception as e:
		log.error(f"Error processing WooCommerce Order: {e}")

	return jsonify({'message': 'OK'}), 200
