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


@api.route('/heroes', methods=['POST'])
def create_hero():
	connection = client.connect(g.db)
	cursor = connection.cursor()
    
	try:
		data = request.get_json()
		name = data['name']
		img = data['img']
		clan_id = data['clan_id']

		if not name:
			return bad_request('Name is not provided')
		if not clan_id:
			return bad_request('Clan ID is not provided')

		hero_id = str(uuid.uuid4())
		cursor.execute("""
			INSERT INTO heroes(
				id,
				name,
				img,
				balance,
				clan_id,
				army
			) VALUES(
				'{id}',
				'{name}',
				'{img}',
				'{balance}',
				'{clan_id}',
				[]
			)
		""".format(
			id=hero_id,
			name=name,
			img=img,
			balance=0,
			clan_id=clan_id
		))

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
		clan = cursor.fetchone()
		
	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()

	data = {
		'id': hero_id,
		'name': name,
		'balance': 0,
		'img': img,
		'army': [],
		'clan': {
			'id': clan[0],
			'name': clan[1],
			'img': clan[2]
		}
	}

	print '\n--> Hero is saved'

	response = make_response(jsonify(data))
	response.status_code = 201
	return response


@api.route('/heroes', methods=['GET'])
def get_heroes():

	connection = client.connect(g.db)
	cursor = connection.cursor()

	try:
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
		""")
		heroes = cursor.fetchall()

		i = 0
		for hero in heroes:
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
			heroes[i][4] = units_descr
			i += 1

	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()

	heroes_data = [{
		'id': el[0],
		'name': el[1],
		'img': el[2],
		'balance': el[3],
		'army': el[4],
		'clan': {
			'id': el[5],
			'name': el[6],
			'img': el[7]
		}
	} for el in heroes]

	response = make_response(jsonify(heroes_data))
	response.status_code = 200
	return response


@api.route('/heroes/<hero_id>', methods=['GET'])
def get_heroe(hero_id):

	connection = client.connect(g.db)
	cursor = connection.cursor()

	try:
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
	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()

	if not hero:
		return ('', 204)

	heroe_data = {
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

	response = make_response(jsonify(heroe_data))
	response.status_code = 200
	return response


@api.route('/heroes/<hero_id>', methods=['PUT'])
def update_hero(hero_id):

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
			UPDATE heroes
			SET army=[{army}]
			WHERE id='{hero_id}'
		""".format(
			hero_id=hero_id,
			army=army_sql
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
	except Exception, error:
		print 'ERROR: ', error
		return bad_request(error)
	finally:
		cursor.close()
		connection.close()

	heroe_data = {
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

	response = make_response(jsonify(heroe_data))
	response.status_code = 200
	return response
