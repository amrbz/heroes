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


@api.route('/mines', methods=['POST'])
def create_mine():

	connection = client.connect(g.db)
	cursor = connection.cursor()

	try:
		data = request.get_json()
		name = data['name']
		img = data['img']
		lat = data['lat']
		lng = data['lng']
		freq = data['freq']
		qty = data['qty']
		mine_id = str(uuid.uuid4())

		location = """
			{{
				lat='{lat}',
				lng={lng}
			}}
		""".format(
			lat=lat,
			lng=lng
		)
		
		production = """
			{{
				freq='{freq}',
				qty={qty}
			}}
		""".format(
			freq=freq,
			qty=qty
		)

		cursor.execute("""
			INSERT INTO mines(
				id,
				name,
				img,
				location,
				production,
				army
			) VALUES(
				'{id}',
				'{name}',
				'{img}',
				{location},
				{production},
				[]
			)
		""".format(
			id=mine_id,
			name=name,
			img=img,
			location=location,
			production=production
		))
		
	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()

	data = {
		'id': mine_id,
		'name': name,
		'hero': None,
		'img': img,
		'location': {
			'lat': lat,
			'lng': lng
		},
		'production': {
			'qty': qty,
			'freq': freq
		},
		'army': []
	}

	print '\n--> Mine is created'

	response = make_response(jsonify(data))
	response.status_code = 201
	return response


@api.route('/mines', methods=['GET'])
def get_mines():

	connection = client.connect(g.db)
	cursor = connection.cursor()

	try:
		cursor.execute("""
			SELECT 
				m.id,
				m.name,
				m.img,
				m.location,
				m.production,
				m.army,
				h.id,
				h.name,
				c.id,
				c.name,
				c.img
			FROM mines m
			LEFT JOIN heroes h ON m.hero_id = h.id
			LEFT JOIN clans c ON h.clan_id = c.id
			ORDER BY m.name
		""")
		mines = cursor.fetchall()

		i = 0
		for mine in mines:
			units_descr = []
			for unit in mine[5]:
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
					'unit': {
						'id':data[0],
						'name':data[1],
						'img':data[2],
						'health':data[3],
						'attack':data[4],
						'price':data[5]
					},
					'qty': unit['qty']
				})
			mines[i][5] = units_descr
			i += 1


	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()



	units_data = [{
		'mine': {
			'id':el[0],
			'name':el[1],
			'img':el[2],
			'location':el[3],
			'production':el[4],
			'army': el[5]
		},
		'hero': {
			'id': el[6],
			'name': el[7]
		},
		'clan': {
			'id': el[8],
			'name': el[9],
			'img': el[10]
		}
	} for el in mines]


	response = make_response(jsonify(units_data))
	response.status_code = 200
	return response


@api.route('/mines/<mine_id>', methods=['GET'])
def get_mine(mine_id):

	connection = client.connect(g.db)
	cursor = connection.cursor()

	try:
		cursor.execute("""
			SELECT 
				m.id,
				m.name,
				m.img,
				m.location,
				m.production,
				m.army,
				h.id,
				h.name,
				c.id,
				c.name,
				c.img
			FROM mines m
			LEFT JOIN heroes h ON m.hero_id = h.id
			LEFT JOIN clans c ON h.clan_id = c.id
			WHERE m.id='{mine_id}'
		""".format(
			mine_id=mine_id
		))
		mine = cursor.fetchone()

		units_descr = []
		for unit in mine[5]:
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
				'unit': {
					'id':data[0],
					'name':data[1],
					'img':data[2],
					'health':data[3],
					'attack':data[4],
					'price':data[5]
				},
				'qty': unit['qty']
			})
		mine[5] = units_descr

	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()

	if not mine:
		print '-> No data found'
		return ('', 204)

	data = {
		'mine': {
			'id': mine[0],
			'name': mine[1],
			'img': mine[2],
			'location': mine[3],
			'production': mine[4],
			'army': mine[5]
		},
		'hero': {
			'id': mine[6],
			'name': mine[7]
		},
		'clan': {
			'id': mine[8],
			'name': mine[9],
			'img': mine[10]
		}
	}

	response = make_response(jsonify(data))
	response.status_code = 200
	return response


@api.route('/mines/<mine_id>', methods=['PUT'])
def update_mine(mine_id):

	connection = client.connect(g.db)
	cursor = connection.cursor()

	data = request.get_json()
	army = data['army']

	army_sql = ''
	for unit in army:
		el = """
                {{
					unit_id='{unit_id}',
					qty={qty}
				}}
            """.format(
				unit_id=unit['unitId'],
				qty=unit['qty']
			)
		army_sql = el if army_sql == '' else ','.join((army_sql, el))

	try:
		print '--> Selecting mines data'
		cursor.execute("""
			UPDATE mines
			SET army=[{army}]
			WHERE id='{mine_id}'
		""".format(
			mine_id=mine_id,
			army=army_sql
		))
		cursor.execute("""REFRESH TABLE mines""")
		cursor.execute("""
			SELECT 
				m.id,
				m.name,
				m.img,
				m.location,
				m.production,
				m.army,
				h.id,
				h.name,
				c.id,
				c.name,
				c.img
			FROM mines m
			LEFT JOIN heroes h ON m.hero_id = h.id
			LEFT JOIN clans c ON h.clan_id = c.id
			WHERE m.id='{mine_id}'
		""".format(
			mine_id=mine_id
		))
		mine = cursor.fetchone()

		units_descr = []
		for unit in mine[5]:
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
				'unit': {
					'id':data[0],
					'name':data[1],
					'img':data[2],
					'health':data[3],
					'attack':data[4],
					'price':data[5]
				},
				'qty': unit['qty']
			})
		mine[5] = units_descr

	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()


	data = {
		'mine': {
			'id': mine[0],
			'name': mine[1],
			'img': mine[2],
			'location': mine[3],
			'production': mine[4],
			'army': mine[5]
		},
		'hero': {
			'id': mine[6],
			'name': mine[7]
		},
		'clan': {
			'id': mine[8],
			'name': mine[9],
			'img': mine[10]
		}
	}

	response = make_response(jsonify(data))
	response.status_code = 200
	return response



@api.route('/mines/attack', methods=['POST'])
def attack_mine():
	
	connection = client.connect(g.db)
	cursor = connection.cursor()

	data = request.get_json()
	hero_id = data['heroId']
	mine_id = data['mineId']
	mine_army_sql = ''
	hero_army_sql = ''

	if not hero_id:
		return bad_request('Hero ID is not provided')

	if not mine_id:
		return bad_request('Mine ID id not provided')

	try:
		cursor.execute("""
			SELECT 
				h.army
			FROM heroes h
			WHERE id='{hero_id}'
		""".format(
			hero_id=hero_id
		))
		hero_data = cursor.fetchone()
		hero_army = hero_data[0]

		cursor.execute("""
			SELECT 
				m.army, 
				m.hero_id
			FROM mines m
			WHERE id='{mine_id}'
		""".format(
			mine_id=mine_id
		))
		mine_data = cursor.fetchone()
		mine_army = mine_data[0]
		mine_hero = mine_data[1]

		cursor.execute("""
			SELECT id, attack
			FROM units
			ORDER BY attack
		""")
		units = cursor.fetchall()

		hero_attack = 0
		for hero_unit in hero_army:
			for unit in units:
				if unit[0] == hero_unit['unit_id']:
					hero_attack +=  hero_unit['qty'] * unit[1]
					break
		
		mine_attack = 0
		for mine_unit in mine_army:
			for unit in units:
				if unit[0] == mine_unit['unit_id']:
					mine_attack +=  mine_unit['qty'] * unit[1]
					break
		# print hero_attack, mine_attack
		if hero_attack >= mine_attack:
			diff = mine_attack
			mine_army = []
			for unit in units:
				i = 0
				for hero_unit in hero_army:
					if unit[0] == hero_unit['unit_id']:
						killed, remainder = divmod(diff, unit[1])
						if killed >= hero_unit['qty']:
							print '--> Removing unit because all killed'
							diff -= hero_unit['qty'] * unit[1]
							del hero_army[i]
						elif killed > 0:
							print '--> Updating unit qty from {0} to {1}'.format(hero_unit['qty'], hero_unit['qty'] - killed)
							hero_army[i] = {
								'unit_id': hero_unit['unit_id'],
								'qty': hero_unit['qty'] - killed
							}
						break
					i += 1

			for unit in hero_army:
				el = """
						{{
							unit_id='{unit_id}',
							qty={qty}
						}}
					""".format(
						unit_id=unit['unit_id'],
						qty=unit['qty']
					)
				hero_army_sql = el if hero_army_sql == '' else ','.join((hero_army_sql, el))
		else:
			diff = hero_attack
			hero_army = []
			for unit in units:
				i = 0
				for mine_unit in mine_army:
					if unit[0] == mine_unit['unit_id']:
						killed, remainder = divmod(diff, unit[1])
						if killed >= mine_unit['qty']:
							print '--> Removing unit because all killed'
							diff -= mine_unit['qty'] * unit[1]
							del mine_army[i]
						elif killed > 0:
							print '--> Updating unit qty from {0} to {1}'.format(mine_unit['qty'], mine_unit['qty'] - killed)
							diff -= killed * unit[1]
							mine_army[i] = {
								'unit_id': mine_unit['unit_id'],
								'qty': mine_unit['qty'] - killed
							}
						break
					i += 1
			
			for unit in mine_army:
				el = """
						{{
							unit_id='{unit_id}',
							qty={qty}
						}}
					""".format(
						unit_id=unit['unit_id'],
						qty=unit['qty']
					)
				mine_army_sql = el if mine_army_sql == '' else ','.join((mine_army_sql, el))

		cursor.execute("""
			UPDATE heroes
			SET army=[{army}]
			WHERE id='{hero_id}'
		""".format(
			army=hero_army_sql,
			hero_id=hero_id
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

		cursor.execute("""
			UPDATE mines
			SET 
				army=[{army}],
				hero_id='{hero_id}'
			WHERE id='{mine_id}'
		""".format(
			army=mine_army_sql,
			mine_id=mine_id,
			hero_id= hero[0] if hero_attack >= mine_attack else mine_hero
		))
		cursor.execute("""REFRESH TABLE mines""")
		cursor.execute("""
			SELECT 
				m.id,
				m.name,
				m.img,
				m.location,
				m.production,
				m.army
			FROM mines m
			WHERE m.id='{mine_id}'
		""".format(
			mine_id=mine_id
		))
		mine = cursor.fetchone()

		units_descr = []
		for unit in mine[5]:
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
				'unit': {
					'id':data[0],
					'name':data[1],
					'img':data[2],
					'health':data[3],
					'attack':data[4],
					'price':data[5]
				},
				'qty': unit['qty']
			})
		mine[5] = units_descr
			
		
		
	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()


	hero_data = {
		'hero': {
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
		},
		'mine': {
			'id': mine[0],
			'name': mine[1],
			'img': mine[2],
			'location': mine[3],
			'production': mine[4],
			'army': mine[5]
		}
	}

	response = make_response(jsonify(hero_data))
	response.status_code = 200
	return response