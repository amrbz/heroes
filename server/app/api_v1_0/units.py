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


@api.route('/units', methods=['POST'])
def create_unit():

	connection = client.connect(g.db)
	cursor = connection.cursor()
    
	try:
		data = request.get_json()
		name = data['name']
		img = data['img'] 
		health = data['health']
		attack = data['attack']
		price = data['price']
		unit_id = str(uuid.uuid4())
		cursor.execute("""
			INSERT INTO units(
				id,
				name,
				img,
				health,
				attack,
				price
			) VALUES(
				'{id}',
				'{name}',
				'{img}',
				'{health}',
				'{attack}',
				'{price}'
			)
		""".format(
			id=unit_id,
			name=name,
			img=img,
			health=health,
			attack=attack,
			price=price
		))
		
	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()

	data = {
		'id': unit_id,
		'name': name,
		'img': img,
		'health': health,
		'attack': attack,
		'price': price
	}

	print '\n--> Unit is created'

	response = make_response(jsonify(data))
	response.status_code = 201
	return response


@api.route('/units', methods=['GET'])
def get_units():

	connection = client.connect(g.db)
	cursor = connection.cursor()


	try:
		cursor.execute("""
			SELECT 
				id,
				name,
				img,
				health,
				attack,
				price
			FROM units
			ORDER BY name
		""")
		units = cursor.fetchall()

	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()


	units_data = [{
		'id':el[0],
		'name':el[1],
		'img':el[2],
		'health':el[3],
		'attack':el[4],
		'price':el[5]
	} for el in units]


	response = make_response(jsonify(units_data))
	response.status_code = 200
	return response


@api.route('/units/<unit_id>', methods=['GET'])
def get_unit(unit_id):

	print '\n--> Fetching file data init'

	connection = client.connect(g.db)
	cursor = connection.cursor()

	try:
		print '--> Selecting clan data'
		cursor.execute("""
			SELECT 
				id,
				name,
				img,
				health,
				attack,
				price
			FROM units
			WHERE id='{unit_id}'
		""".format(
			unit_id=unit_id
		))
		unit = cursor.fetchone()
	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()

	if not unit_id:
		print '-> No data found'
		return ('', 204)

	data = {
		'id':unit[0],
		'name':unit[1],
		'img':unit[2],
		'health':unit[3],
		'attack':unit[4],
		'price':unit[5]
	}

	response = make_response(jsonify(data))
	response.status_code = 200
	return response


@api.route('/units/buy', methods=['POST'])
def buy_unit():

	print '\n--> Fetching file data init'

	connection = client.connect(g.db)
	cursor = connection.cursor()

	data = request.get_json()
	unit_id = data['unitId']
	hero_id = data['heroId'] 
	qty = int(data['qty'])

	if qty < 1:
		return bad_request("Qty must be greater than zero")

	if not unit_id:
		return bad_request("Unit ID is not provided")

	if not hero_id:
		return bad_request("Hero ID is not provided")

	try:
		print '--> Selecting unit data'
		cursor.execute("""
			SELECT price
			FROM units
			WHERE id='{unit_id}'
		""".format(
			unit_id=unit_id
		))
		unit_price = cursor.fetchone()[0]

		print '--> Selecting hero data'
		cursor.execute("""
			SELECT 
				h.balance,
				h.army
			FROM heroes h
			WHERE h.id='{hero_id}'
		""".format(
			hero_id=hero_id
		))
		hero = cursor.fetchone()

		# print hero[0], unit_price, qty, unit_price * qty

		if int(hero[0]) >= int(unit_price * qty):

			print '--> Updating army'
			unit_in_stock = False
			for unit in hero[1]:
				if unit_id == unit['unit_id']:
					unit_in_stock = True
					break

			army = hero[1]
			if unit_in_stock == False:
				army.append({
					'unit_id': unit_id,
					'qty': qty
				})

			print 'QTY', qty

			army_sql = ''
			for unit in army:
				el = """
						{{
							unit_id='{unit_id}',
							qty={qty}
						}}
					""".format(
						unit_id=unit['unit_id'],
						qty=unit['qty'] + qty if unit_in_stock and unit['unit_id'] == unit_id else unit['qty']
					)
				army_sql = el if army_sql == '' else ','.join((army_sql, el))

			balance = int(hero[0]) - int(unit_price * qty)

			cursor.execute("""
				UPDATE heroes
				SET army=[{army}],
					balance='{balance}'
				WHERE id='{hero_id}'
			""".format(
				hero_id=hero_id,
				army=army_sql,
				balance=balance
			))
			cursor.execute("""REFRESH TABLE heroes""")
			cursor.execute("""
				SELECT 
					h.id,
					h.name,
					h.img,
					h.balance,
					h.army,
					c.id,
					c.name,
					c.img
				FROM heroes h
				LEFT JOIN clans c ON c.id = h.clan_id
				WHERE h.id='{hero_id}'
			""".format(
				hero_id=hero_id
			))
			hero = cursor.fetchone()

			units_descr = []
			for unit in hero[4]:
				cursor.execute("""
					SELECT 
						id, 
						name,
						img,
						health,
						attack,
						price
					FROM units
					WHERE id='{unit_id}'
				""".format(
					unit_id=unit['unit_id']
				))
				data = cursor.fetchone()
				units_descr.append({
					'unut': {
						'id':data[0],
						'name':data[1],
						'img':data[2],
						'health':data[3],
						'attack':data[4],
						'price':data[5]
					},
					'qty': unit['qty']
				})
			hero[4] = units_descr
		else:
			return bad_request('Not enough money')

	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()

	if not unit:
		print '-> No data found'
		return ('', 204)

	if not hero:
		print '-> No data found'
		return ('', 204)

	

	data = {
		'id': hero[0],
		'name': hero[1],
		'img': hero[2],
		'balance': hero[3],
		'army': hero[4],
		'clan': {
			'id': hero[5],
			'name': hero[6],
			'img': hero[7]
		}
	}

	response = make_response(jsonify(data))
	response.status_code = 200
	return response
