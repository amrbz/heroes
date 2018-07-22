# -*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import ipfsapi
import uuid
import time
import requests
import hashlib
import io
import os
from crate import client
import base64
import pywaves as pw
import signal
import magic

from . import api
from flask import jsonify, request, g, abort, make_response
from errors import bad_request, validation_error, unavailable


@api.route('/clans', methods=['POST'])
def create_clan():

	connection = client.connect(g.db)
	cursor = connection.cursor()
    
	try:
		data = request.get_json()
		name = data['name']
		img = data['img']

		clan_id = str(uuid.uuid4())
		cursor.execute("""
			INSERT INTO clans(
				id,
				name,
				img
			) VALUES(
				'{id}',
				'{name}',
				'{img}'
			)
		""".format(
			id=clan_id,
			name=name,
			img=img
		))
		
	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()

	data = {
		'id': clan_id,
		'name': name,
		'img': img
	}

	print '\n--> Clan is created'

	response = make_response(jsonify(data))
	response.status_code = 201
	return response


@api.route('/clans', methods=['GET'])
def get_clans():

	connection = client.connect(g.db)
	cursor = connection.cursor()


	try:
		print '--> Selecting files'
		cursor.execute("""
			SELECT 
				id,
				name,
				img
			FROM clans
			ORDER BY name
		""")
		clans = cursor.fetchall()

	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()


	clans_data = [{
		'id': el[0],
		'name': el[1],
		'img': el[2]
	} for el in clans]


	response = make_response(jsonify(clans_data))
	response.status_code = 200
	return response


@api.route('/clans/<clan_id>', methods=['GET'])
def get_clan(clan_id):

	print '\n--> Fetching file data init'

	connection = client.connect(g.db)
	cursor = connection.cursor()

	try:
		print '--> Selecting clan data'
		cursor.execute("""
			SELECT 
				id,
				name,
				img
			FROM clans
			WHERE id='{clan_id}'
		""".format(
			clan_id=clan_id
		))
		clan_data = cursor.fetchone()
	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()

	if not clan_data:
		print '-> No data found'
		return ('', 204)

	data = {
		'id': clan_data[0],
		'name': clan_data[1],
		'img': clan_data[2]
	}


	response = make_response(jsonify(data))
	response.status_code = 200
	return response
