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
		supply = data['supply']
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
				supply,
				army
			) VALUES(
				'{id}',
				'{name}',
				'{img}',
				{location},
				{production},
				'{supply}',
				[]
			)
		""".format(
			id=mine_id,
			name=name,
			img=img,
			location=location,
			production=production,
			supply=supply
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
		'army': [],
		'supply': supply,
		'collected': None
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
				m.supply,
				m.collected,
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
			'army': el[5],
			'supply': el[6],
			'collected': el[7]
		},
		'hero': {
			'id': el[8],
			'name': el[9]
		},
		'clan': {
			'id': el[10],
			'name': el[11],
			'img': el[12]
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
				m.supply,
				m.collected,
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
			'army': mine[5],
			'supply': mine[6],
			'collected': mine[7]
		},
		'hero': {
			'id': mine[8],
			'name': mine[9]
		},
		'clan': {
			'id': mine[10],
			'name': mine[11],
			'img': mine[12]
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
				m.supply,
				m.collected,
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
			'army': mine[5],
			'supply': mine[6],
			'collected': mine[7]
		},
		'hero': {
			'id': mine[8],
			'name': mine[9]
		},
		'clan': {
			'id': mine[10],
			'name': mine[11],
			'img': mine[12]
		}
	}

	response = make_response(jsonify(data))
	response.status_code = 200
	return response


def battle(
	hero_id, 
	mine_id, 
	hero_health=None, 
	hero_attack=None,  
	mine_health=None, 
	mine_attack=None):
	hero_army_sql = ''
	mine_army_sql = ''

	connection = client.connect(g.db)
	cursor = connection.cursor()

	cursor.execute("""
		SELECT id, attack, health
		FROM units
		ORDER BY attack
	""")
	units = cursor.fetchall()

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

	if not hero_health:
		hero_health = 0
		hero_attack = 0
		for hero_unit in hero_army:
			for unit in units:
				if unit[0] == hero_unit['unit_id']:
					hero_attack +=  hero_unit['qty'] * int(unit[1])
					hero_health +=  hero_unit['qty'] * int(unit[2])
					break
	
	if not mine_health:
		mine_health = 0
		mine_attack = 0
		for mine_unit in mine_army:
			for unit in units:
				if unit[0] == mine_unit['unit_id']:
					mine_attack +=  mine_unit['qty'] * int(unit[1])
					mine_health +=  mine_unit['qty'] * int(unit[2])
					break

	mine_health -= hero_attack
	hero_health -= mine_attack

	
	if hero_health <= 0 or mine_health <= 0:
		army = hero_army if hero_health > 0 else mine_army
		health_left = hero_health if hero_health > 0 else mine_health

		for unit in units:
			unit_health = unit[2]
			for army_unit in army:
				if army_unit['unit_id'] == unit[0]:
					row_health = int(army_unit['qty']) * int(unit_health)
					if health_left < row_health:
						killed = int((row_health-health_left)*1.0/row_health * int(army_unit['qty']))
						army[0] = {
							'unit_id': army_unit['unit_id'],
							'qty': army_unit['qty'] - killed
						}
						print 'LAT ROW', killed
					else:
						print '--> Deleted', units[0][0]
						del army[0]
					break

		army_sql = ''
		for unit in army:
			el = """
					{{
						unit_id='{unit_id}',
						qty={qty}
					}}
				""".format(
					unit_id=unit['unit_id'],
					qty=unit['qty']
				)
			army_sql = el if army_sql == '' else ','.join((army_sql, el))

		
		hero_army_sql = army_sql if hero_health > 0 else ''
		mine_army_sql = army_sql if mine_health > 0 else ''
		
		return hero_army_sql, mine_army_sql
	else:
		return battle(
			hero_id,
			mine_id, 
			hero_health,
			hero_attack, 
			mine_health,
			mine_attack
		)


@api.route('/mines/attack', methods=['POST'])
def attack_mine():
	
	connection = client.connect(g.db)
	cursor = connection.cursor()

	data = request.get_json()
	hero_id = data['heroId']
	mine_id = data['mineId']

	if not hero_id:
		return bad_request('Hero ID is not provided')

	if not mine_id:
		return bad_request('Mine ID id not provided')

	try:
		hero_army_sql, mine_army_sql = battle(hero_id, mine_id)

		cursor.execute("""
			UPDATE heroes
			SET army=[{army}]
			WHERE id='{hero_id}'
		""".format(
			army=hero_army_sql,
			hero_id=hero_id
		))
		cursor.execute("""REFRESH TABLE heroes""")

		if mine_army_sql == '':
			cursor.execute("""
				UPDATE mines
				SET 
					army=[{army}],
					hero_id='{hero_id}'
				WHERE id='{mine_id}'
			""".format(
				army=mine_army_sql,
				mine_id=mine_id,
				hero_id=hero_id
			))
		else:
			cursor.execute("""
				UPDATE mines
				SET 
					army=[{army}]
				WHERE id='{mine_id}'
			""".format(
				army=mine_army_sql,
				mine_id=mine_id
			))
		cursor.execute("""REFRESH TABLE mines""")

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
		hero[4] = units_descr

		
		cursor.execute("""
			SELECT 
				m.id,
				m.name,
				m.img,
				m.location,
				m.production,
				m.army,
				m.supply,
				m.collected
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
			'army': mine[5],
			'supply': mine[6],
			'collected': mine[7]
		}
	}

	response = make_response(jsonify(hero_data))
	response.status_code = 200
	return response


@api.route('/mines/collect', methods=['POST'])
def collect_mine():
	connection = client.connect(g.db)
	cursor = connection.cursor()

	data = request.get_json()
	hero_id = data['heroId']
	mine_id = data['mineId']

	try:
		cursor.execute("""
			SELECT 
				created,
				collected,
				production
			FROM mines
			WHERE id='{mine_id}'
		""".format(
			mine_id=mine_id
		))
		mine = cursor.fetchone()
		now = int(time.time())

		created = int(mine[0])
		collected = int(mine[1]) if mine[1] else now
		production = mine[2]

		diff = collected-created
		iterations =  int(diff*1.0/production['freq'])
		balance = int(iterations * production['qty'])

		cursor.execute("""
			SELECT 
				balance
			FROM heroes
			WHERE id='{hero_id}'
		""".format(
			hero_id=hero_id
		))
		hero = cursor.fetchone()

		print 'BAL', hero[0]

		cursor.execute("""
			UPDATE heroes
			SET balance='{balance}'
			WHERE id='{hero_id}'
		""".format(
			hero_id=hero_id,
			balance=balance+int(hero[0])
		))
		cursor.execute("""REFRESH TABLE heroes""")

		cursor.execute("""
			UPDATE mines
			SET collected='{collected}'
			WHERE id='{mine_id}'
		""".format(
			mine_id=mine_id,
			collected=int(time.time())
		))
		cursor.execute("""REFRESH TABLE mines""")

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
		hero[4] = units_descr

		
		cursor.execute("""
			SELECT 
				m.id,
				m.name,
				m.img,
				m.location,
				m.production,
				m.army,
				m.supply,
				m.collected
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


	data = {
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
			'army': mine[5],
			'supply': mine[6],
			'collected': mine[7]
		}
	}

	response = make_response(jsonify(data))
	response.status_code = 200
	return response