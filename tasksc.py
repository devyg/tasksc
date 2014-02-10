#!/usr/bin/eval PYTHONPATH=/home/yanng/modules python
# -*- coding: utf-8 -*-

"""
The Tasks Capacitor by devyg.fr.

A Trello-like made with web.py.
"""

import sys, os
#abspath = os.path.dirname(__file__)
#sys.path.append(abspath)
#os.chdir(abspath)

import random
import string
from datetime import datetime, timedelta
import hashlib

import site
site.addsitedir('/home/yanng/modules')

import web
from web import form as wform

import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId
from gridfs import GridFS

# DB variables

# dev
# PROD = False
#DB_ADDR = 'localhost'
#DB_PORT = 27017
#DB_NAME = ''
#DB_FILES = ''

# prod
PROD = True
DB_ADDR = ''
DB_PORT = 27017
DB_NAME = ''
DB_FILES = ''
DB_USER = ''
DB_PASSWD = ''

#'/(.*)/', 'redirect',
urls = (
	'/', 'Index',
	'/index', 'Index',
	'/login', 'Login',
	'/logout', 'Logout',
	'/doh', 'Doh',
	'/user/add/', 'AddUser',
	'/user/delete/(\w+)', 'DeleteUser',
	'/user/edit/(\w+)', 'EditUser',
	'/user/account/(\w+)', 'UserAccount',
	'/board/add/', 'AddBoard',
	'/board/(\w+)/delete/', 'DeleteBoard',
	'/board/(\w+)/edit/', 'EditBoard',
	'/board/(\w+)/', 'Board',
	'/board/(\w+)/tasklist/add', 'AddTaskList',
	'/board/(\w+)/tasklist/(\w+)/delete/', 'DeleteTaskList',
	'/board/(\w+)/tasklist/(\w+)/archive/', 'ArchiveTaskList',
	'/board/(\w+)/tasklist/(\w+)/edit/', 'EditTaskList',
	'/board/(\w+)/tasklist/(\w+)/card/add', 'AddCard',
	'/tasklist/(\w+)/cards/', 'Cards',
	'/card/(\w+)/delete/', 'DeleteCard',
	'/card/(\w+)/edit/', 'EditCard',
	'/card/(\w+)/move/list/(\w+)/', 'MoveCardToList',
	'/card/(\w+)/', 'Card',
	'/card/(\w+)/file/upload/', 'CardFileUp',
	'/card/(\w+)/comment/add/', 'AddComment',
	'/card/(\w+)/comments/', 'CardComments',
	'/card/(\w+)/file/(\w+)/get/', 'GetFile',
	'/card/(\w+)/file/(\w+)/delete/', 'DeleteFile' )

# webpy

web.config.debug = False

def unauthorized():
	return web.unauthorized(render.doh('401 - Authorization required'))

def forbidden():
	return web.forbidden(render.doh('403 - Access forbidden'))

def notfound():
	return web.notfound(render.doh('Hey, Doc, we better back up. This page does not exist.<br>404 - Page not found'))

def internalerror():
	return web.internalerror(render.doh(' Oh, this is heavy.<br>500 - FATAL ERROR.'))

app = web.application(urls, globals())
app.unauthorized = unauthorized
app.forbidden = forbidden
app.notfound = notfound
#app.internalerror = internalerror

# renders

#web.ctx.session = sessions
#web.template.Template.globals['sessions'] = sessions

render = web.template.render('templates/', base='layout')
render_part = web.template.render('templates/')

web.template.Template.globals['render_part'] = render_part

web.template.Template.globals['app_name'] = 'The Tasks Capacitor'
web.template.Template.globals['version'] = '0.1'
web.template.Template.globals['author'] = 'Devyg'
web.template.Template.globals['year'] = '2013'

# session tools

def current_session():
	# get current user cookie value
	session_id = None

	session_id = web.cookies().get('tasksc')
	if not session_id:
		raise web.seeother('/login?next=')

	# check if session is not expired
	session_db = None
	db = TCMongoDB()

	try:
		db.set_col('sessions')
		db.col.ensure_index('id')
		session_db = db.col.find_one({'id': session_id})
	except Exception, e:
		raise web.internalerror(str(e))
	finally:
		db.close_client()

	if not session_db:
		raise web.seeother('/login')

	return session_db

def current_user(key):
	cur_session = current_session()

	if key == 'id':
		return cur_session['user_id']

	db = TCMongoDB()

	# get user data in db
	try:
		db.set_col('users')
		cur_user = db.col.find_one({'_id': cur_session['user_id']})
	except Exception, e:
		raise web.internalerror(str(e))
	finally:
		db.close_client()

	if not cur_user.has_key(key):
		raise AttributeError('Key %s not found.' % key)

	return cur_user[key]

# security
# inspired from waltz
# https://github.com/mekarpeles/waltz


def _rand(chars=string.ascii_letters+string.digits, length=16):
	return ''.join(random.choice(chars) for x in range(length))

def _salt(chars=string.ascii_letters+string.digits, length=12):
	return _rand(length=12)

def _digest(tohash, hashl=hashlib.sha256):
	return hashl(tohash).hexdigest()

# validators

class Validators:
	is_email = wform.regexp(r'^[a-zA-Z0-9._-]+@[a-z0-9._-]{2,}\.[a-z]{2,4}$', 'Invalid e-mail address')


# tool class for mongodb connection

class TCMongoDB(object):
	"""
	Handling classes will inherit from this class.
	It gives useful tools for mongodb connections.
	"""

	def __init__(self):
		self.client = None
		self.db = None
		self.col = None
		self.grid_db = None
		self.fs = None

	def init_client(self):
		self.client = MongoClient(DB_ADDR, DB_PORT)
		"""
		try:
			self.client = MongoClient(DB_ADDR, DB_PORT)
		except pymongo.errors.ConnectionFailure, e:
			return False
		return True
		"""

	def close_client(self):
		if self.client:
			self.client.disconnect()

	def set_db(self, db_name=None):
		"""Sets current db. I no client, try to connect to db"""
		if not self.client:
			self.init_client()
		self.db = self.client[DB_NAME if not db_name else db_name]
		
		if PROD:
			self.db.authenticate(DB_USER, DB_PASSWD, DB_NAME)
		
	def set_col(self, col):
		"""Sets the collection. If db not selected, try to select default db"""
		if not self.db:
			self.set_db()
		self.col = self.db[col]

	# GridFS functions

	def set_grid_db(self, db_name=None):
		if not self.client:
			self.init_client()
		self.grid_db = self.client[DB_FILES if not db_name else db_name]
		
		if PROD:
			self.grid_db.authenticate(DB_USER, DB_PASSWD, DB_FILES)

	def set_grid(self, db_name=None):
		self.set_grid_db(db_name)

	def set_fs(self, db=None):
		self.fs = GridFS(self.grid_db if not db else db)


# Decorators

def auth(target):
	"""
	Decorator for site sections that need authentication.
	"""

	def wrapper(*args, **kwargs):
		session_db = current_session()

		# check session expiration date
		if not session_db['date'] + timedelta(hours=6) > datetime.now():
			# we do not remove the entry yet it will be done when the user succefully logs again
			raise web.seeother('/login')

		return target(*args, **kwargs)

	return wrapper

def restrict():
	"""
	Decorator for site sections that need level restriction.
	"""
	pass


# Handling classes

class redirect:
    def GET(self, path):
        web.seeother('/' + path)


class Doh(object):
	def GET(self):
		return render.doh('!!!')


class Index(TCMongoDB):
	@auth
	def GET(self):
		try:
			self.set_col('users')
			users = self.col.find()

			self.set_col('boards')
			boards = self.col.find()
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		return render.index(users, boards)


class Login(TCMongoDB):
	login_form = wform.Form(
		wform.Textbox('login', wform.notnull, description='Login', class_='input-xlarge'),
		wform.Password('password', wform.notnull, description='Password', class_='input-xlarge'),
		wform.Button('Login', type='submit', description='Login', class_='btn'))

	def GET(self):
		return render.login(self.login_form())

	def POST(self):
		form = self.login_form()
		if not form.validates():
			return render.login(form)

		user = None
		try:
			self.set_col('users')
			user = self.col.find_one({'login': form.login.value})
		except Exception, e:
			return render.doh(str(e))

		if not user or user['password'] != _digest(form.password.value + user['salt']):
			form.note = 'Authentication failed'
			return render.login(form)

		# generating new session id
		session_id = _rand()

		try:
			# check if user already has entry then saving session in db
			self.set_col('sessions')

			self.col.ensure_index('user_id')
			session_entry = self.col.find_one({'user_id': user['_id']})
			if session_entry:
				self.col.remove({'user_id': user['_id']})

			session = {'id': session_id, 'user_id': user['_id'], 'date': datetime.now()}
			self.col.insert(session)
		except Exception, e:
			form.note = str(e)
			return render.login(form)
		finally:
			self.close_client()

		# setting the cookie
		web.setcookie('tasksc', session_id, expires=6000, path='/', domain=None, secure=False)

		return web.seeother('/index')


class Logout(object):
	@auth
	def GET(self):
		db = TCMongoDB()
		try:
			db.set_col('sessions')
			db.col.remove({'_id': current_session()['_id']})
		except Exception, e:
			raise web.internalerror(str(e))
		finally:
			db.close_client()

		web.setcookie('tasksc', '', expires=-1, domain=None, secure=False)

		raise web.seeother('/login')


class AddUser(TCMongoDB):
	user_form = wform.Form(
		wform.Textbox('name', wform.notnull, description='Name', class_='input-xlarge'),
		wform.Textbox('login', wform.notnull, description='Login', class_='input-xlarge'),
		wform.Textbox('email', wform.notnull, Validators.is_email, description='E-mail', class_='input-xlarge'),
		wform.Password('password', wform.notnull, description='Password', class_='input-xlarge'),
		wform.Button('create', type='submit', html='Add', description='Add user', class_='btn'))

	@auth
	def GET(self):
		form = self.user_form()
		return render.adduser(form)

	@auth
	def POST(self):
		form = self.user_form()
		if not form.validates():
			return render.adduser(form)

		salt =  _salt()
		user = {
			'name': form.name.value,
			'login': form.login.value,
			'email': form.email.value,
			'password': _digest(form.password.value + salt),
			'salt': salt,
		}

		try:
			self.set_col('users')
			self.col.ensure_index('login', unique=True)
			self.col.insert(user)
		except pymongo.errors.DuplicateKeyError, e:
			form.note = 'Login already exists'
			return render.adduser(form)
		except Exception, e:
			form.note = 'Unhandled error : ' + str(e)
			return render.adduser(form)
		finally:
			self.close_client()

		raise web.seeother('/index')


class EditUser(TCMongoDB):
	user_form = wform.Form(
		wform.Textbox('name', wform.notnull, description='Name', class_='input-xlarge'),
		wform.Textbox('login', wform.notnull, description='Login', class_='input-xlarge'),
		wform.Textbox('email', wform.notnull, Validators.is_email, description='E-mail', class_='input-xlarge'),
		wform.Password('password', description='Password', class_='input-xlarge'),
		wform.Button('edit', type='submit', html='Edit', description='Edit', class_='btn'))

	@auth
	def GET(self, id):
		return 'TODO'
		user_account = None

		try:
			self.set_col('users')
			self.col.ensure_index('login')
			user_account = self.col.find_one({'_id': ObjectId(id)})
		except Exception, e:
			return str(e)
		finally:
			self.close_client()

		form = self.user_form()
		form.fill(user_account)
		return render.edituser(id, form)

	@auth
	def POST(self, id):
		return 'TODO'
		form = self.user_form()
		if not form.validates():
			return render.edituser(id, form)

		user = {
			'name': form.name.value,
			'login': form.login.value,
			'email': form.email.value,
			'password': '',
		}

		try:
			self.set_col('users')
			self.col.ensure_index('login', unique=True)
			self.col.update({'_id': ObjectId(id)}, {'$set': user})
		except Exception, e:
			form.note = 'Unhandled error : ' + str(e)
			return render.edituser(id, form)
		finally:
			self.close_client()

		raise web.seeother('/index')


class DeleteUser(TCMongoDB):

	del_form = wform.Form(
		wform.Button('delete', type='submit', html='Delete', description='Delete', class_='btn'))

	@auth
	def GET(self, id):
		form = self.del_form()
		return render.deleteuser(id, form)

	@auth
	def POST(self, id):
		try:
			self.set_col('users')
			self.col.ensure_index('login')
			self.col.remove({'_id': ObjectId(id)})
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		raise web.seeother('/index')


class Board(TCMongoDB):
	@auth
	def GET(self, board_id):
		try:
			self.set_col('boards')
			board = self.col.find_one({'_id': ObjectId(board_id)})

			self.set_col('tasklists')
			self.col.ensure_index([('board_id', pymongo.ASCENDING), ('status', pymongo.ASCENDING)])
			tasklists = self.col.find({'board_id': ObjectId(board_id), 'status': 'visible'})

			cards = {}
			# for each tasklist we find associated cards then order them for render
			for t in tasklists:
				db_cards = get_cards(t, 'visible', self)

				ordered_cards = []
				for t_card_id in t['cards']:
					try:
						ordered_cards.append(next(card for card in db_cards.rewind() if card['_id'] == t_card_id))
					except StopIteration:
						pass

				cards.update({t['_id']: unicode(render_part.cards(ordered_cards[::-1]))})
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		return render.board(board, tasklists.clone(), cards)


class AddBoard(TCMongoDB):
	board_form = wform.Form(
		wform.Textbox('title', wform.notnull, description='Title', class_='input-xlarge'),
		wform.Textbox('description', wform.notnull, description='Description', class_='input-xlarge'),
		wform.Button('add', type='submit', html='Add', description='Add board', class_='btn'))

	@auth
	def GET(self):
		form = self.board_form()
		return render.add_board(form)

	@auth
	def POST(self):

		form = self.board_form()
		if not form.validates():
			return render.add_board(form)

		board = {
			'title': form.title.value,
			'description': form.description.value,
			'status': 'visible',
			'creator_id': current_user('id'),
			'lists': []
		}

		try:
			self.set_col('boards')
			self.col.insert(board)
		except Exception, e:
			form.note = 'Unhandled error : ' + str(e)
			return render.add_board(form)
		finally:
			self.close_client()

		raise web.seeother('/index')


class EditBoard(TCMongoDB):
	board_form = wform.Form(
		wform.Textbox('title', wform.notnull, description='Title', class_='input-xlarge'),
		wform.Textbox('description', wform.notnull, description='Description', class_='input-xlarge'),
		wform.Button('edit', type='submit', html='Edit', description='Edit board', class_='btn'))

	@auth
	def GET(self, board_id):
		board = None

		try:
			self.set_col('boards')
			board = self.col.find_one({'_id': ObjectId(board_id)})
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		form = self.board_form()
		form.fill(board)
		return render.edit_board(board_id, form)

	@auth
	def POST(self, board_id):
		form = self.board_form()
		if not form.validates():
			return render.edit_board(board_id, form)

		board = {
			'title': form.title.value,
			'description': form.description.value,
		}

		try:
			self.set_col('boards')
			self.col.update({'_id': ObjectId(board_id)}, {'$set': board})
		except Exception, e:
			form.note = 'Unhandled error : ' + str(e)
			return render.edit_board(board_id, form)
		finally:
			self.close_client()

		raise web.seeother('/board/%s/' % board_id)


class DeleteBoard(TCMongoDB):

	del_form = wform.Form(
		wform.Button('delete', type='submit', html='Delete', description='Delete', class_='btn'))

	@auth
	def GET(self, id):
		form = self.del_form()
		return render.delete_board(id, form)

	@auth
	def POST(self, id):
		# erase linked tasks lits

		return 'Soon'

		"""
		try:
			self.init_col('users')
			self.col.ensure_index('login')
			self.col.remove({'_id': ObjectId(id)})
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		raise web.seeother('/index')
		"""


class AddTaskList(TCMongoDB):
	tasklist_form = wform.Form(
		wform.Textbox('title', wform.notnull, description='Title', class_='input-xlarge'),
		wform.Textbox('description', wform.notnull, description='Description', class_='input-xlarge'),
		wform.Button('add', type='submit', html='Add', description='Add task list', class_='btn'))

	@auth
	def GET(self, board_id):
		form = self.tasklist_form()
		return render.add_tasklist(board_id, form)

	@auth
	def POST(self, board_id):
		form = self.tasklist_form()
		if not form.validates():
			return render.add_tasklist(board_id, form)

		tasklist = {
			'title': form.title.value,
			'description': form.description.value,
			'status': 'visible',
			'board_id': ObjectId(board_id),
			'creator_id': ObjectId(current_user('id')),
			'cards': []
		}

		try:
			self.set_col('tasklists')
			tl_id = self.col.insert(tasklist)

			self.set_col('boards')
			self.col.update({'_id': ObjectId(board_id)}, {'$push': {'lists': tl_id}})
		except Exception, e:
			form.note = 'Unhandled error : ' + str(e)
			return render.add_tasklist(board_id, form)
		finally:
			self.close_client()

		raise web.seeother('/board/%s/' % board_id)


class EditTaskList(TCMongoDB):
	tasklist_form = wform.Form(
		wform.Textbox('title', wform.notnull, description='Title', class_='input-xlarge'),
		wform.Textbox('description', wform.notnull, description='Description', class_='input-xlarge'),
		wform.Button('edit', type='submit', html='Edit', description='Edit task list', class_='btn'))

	@auth
	def GET(self, board_id, tasklist_id):
		tasklist = None

		try:
			self.set_col('tasklists')
			tasklist = self.col.find_one({'_id': ObjectId(tasklist_id)})
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		if not tasklist:
			return render.doh('Unknown task list')

		form = self.tasklist_form()
		form.fill(tasklist)
		return render.edit_tasklist(board_id, tasklist_id, form)

	@auth
	def POST(self, board_id, tasklist_id):
		form = self.tasklist_form()

		if not form.validates():
			return render.edit_tasklist(board_id, tasklist_id, form)

		tasklist = {
			'title': form.title.value,
			'description': form.description.value,
		}

		try:
			self.set_col('tasklists')
			self.col.update({'_id': ObjectId(tasklist_id)}, {'$set': tasklist})
		except Exception, e:
			form.note = 'Unhandled error : ' + str(e)
			return render.edit_tasklist(board_id, tasklist_id, form)
		finally:
			self.close_client()

		raise web.seeother('/board/%s/' % board_id)


class DeleteTaskList(TCMongoDB):

	del_form = wform.Form(
		wform.Button('delete', type='submit', html='Delete', description='Delete', class_='btn'))

	@auth
	def GET(self, board_id, id):
		form = self.del_form()
		return render.delete_tasklist(board_id, id, form)

	@auth
	def POST(self, board_id, id):
		try:
			# removing cards
			self.set_col('cards')
			self.col.ensure_index('tasklist_id')
			self.col.remove({'tasklist_id': ObjectId(id)})

			# removing tasklist
			self.set_col('tasklists')
			self.col.remove({'_id': ObjectId(id)})
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		raise web.seeother('/board/%s/' % board_id)


class ArchiveTaskList(TCMongoDB):

	arch_form = wform.Form(
		wform.Button('archive', type='submit', html='Archive', description='Archive', class_='btn'))

	@auth
	def GET(self, board_id, tasklist_id):
		form = self.arch_form()
		return render.archive_tasklist(board_id, tasklist_id, form)

	@auth
	def POST(self, board_id, tasklist_id):
		try:
			# archiving cards
			self.set_col('cards')
			self.col.ensure_index('tasklist_id')
			self.col.update({'tasklist_id': ObjectId(tasklist_id)}, {'$set': {'status': 'archive'}})

			# archiving tasklist
			self.set_col('tasklists')
			self.col.update({'_id': ObjectId(tasklist_id)}, {'$set': {'status': 'archive'}})
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		raise web.seeother('/board/%s/' % board_id)


class Card(TCMongoDB):
	@auth
	def GET(self, card_id):
		"""
		TODO: check user right for getting card

		"""
		try:
			self.set_col('cards')
			card = self.col.find_one({'_id': ObjectId(card_id)})
		except Exception, e:
			return render.doh_small(str(e))
		finally:
			self.close_client()

		return render.card(card)


def get_cards(tasklist, status, db=None):
	"""Exceptions has to be managed outside this func"""

	if not db:
		db = TCMongoDB()

	if type(tasklist) == ObjectId:
		db.set_col('tasklists')
		tasklist = db.col.find_one({'_id': ObjectId(tasklist)})

	db.set_col('cards')
	db.col.ensure_index([('board_id', pymongo.ASCENDING), ('tasklist_id', pymongo.ASCENDING), ('status', pymongo.ASCENDING)])
	cards = db.col.find({'board_id': tasklist['board_id'], 'tasklist_id': tasklist['_id'], 'status': status}, {'title': 1, 'description': 1})

	return cards


class Cards(TCMongoDB):
	@auth
	def GET(self, tasklist_id):
		try:
			cards = get_cards(ObjectId(tasklist_id), 'visible', self)
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		return render_part.cards(cards)


class AddCard(TCMongoDB):

	card_form = wform.Form(
		wform.Textbox('title', wform.notnull, description='Title', class_='input-xlarge'),
		wform.Textbox('description', description='Description', class_='input-xlarge'),
		wform.Button('add', type='submit', html='Add', description='Add card', class_='btn')
	)

	@auth
	def GET(self, board_id, tasklist_id):
		form = self.card_form()
		return render_part.add_card(board_id, tasklist_id, form)

	@auth
	def POST(self, board_id, tasklist_id):
		"""How to ?
		register cards positions ?
		check if board and tasklist exist!
		"""

		form = self.card_form()
		if not form.validates():
			return render_part.add_card(board_id, tasklist_id, form)

		card = {
			'status': 'visible',
			'title': form.title.value,
			'description': form.description.value,
			'duedate': None,
			'labels': [],
			'board_id': ObjectId(board_id),
			'tasklist_id': ObjectId(tasklist_id),
			'creator_id': ObjectId(current_user('id')),
			'files': [],
			'comments': []
		}

		try:
			self.set_col('tasklists')
			card_tl = self.col.find_one({'_id': ObjectId(tasklist_id)})
			if not card_tl:
				return render.doh('Unknown tasklist')

			self.set_col('cards')
			card_id = self.col.insert(card)

			self.set_col('tasklists')
			self.col.update({'_id': ObjectId(tasklist_id)}, {'$push': {'cards': card_id}})

		except Exception, e:
			form.note = 'Unhandled error : ' + str(e)
			return render_part.add_card(board_id, tasklist_id, form)
		finally:
			self.close_client()

		return 'Card added'
		#raise web.seeother('/board/%s/' % board_id)

class EditCard(TCMongoDB):

	card_form = wform.Form(
		wform.Textbox('title', wform.notnull, description='Title', class_='edit-input'),
		wform.Textarea('description', description='Description', class_='edit-textarea'),
		wform.Textbox('duedate', description='Due date', class_='edit-input input-date'),
		wform.Button('edit', type='submit', html='Edit', description='Edit', class_='btn')
	)

	def other_tasklists(self, card):
		"""getting other tasklists of the board the card doesn't belong to"""

		self.set_col('tasklists')
		self.col.ensure_index('board_id')
		tasklist = self.col.find_one({'_id': card['tasklist_id']})
		others = self.col.find({'board_id': card['board_id'], '_id': {'$ne': card['tasklist_id']}}, {'title': 1})

		return {'card': tasklist['title'], 'others': others}

	@auth
	def GET(self, card_id):
		card = None

		try:
			self.set_col('cards')
			card = self.col.find_one({'_id': ObjectId(card_id)})

			other_tl = self.other_tasklists(card)
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		if not card:
			return render.doh('Unknown card')

		form = self.card_form()
		form.fill(card)

		return render.edit_card(card, form, other_tl)

	@auth
	def POST(self, card_id):
		form = self.card_form()

		try:
			self.set_col('cards')
			card = self.col.find_one({'_id': ObjectId(card_id)})

			other_tl = self.other_tasklists(card)
		except Exception, e:
			return render.doh(str(e))
		#finally:
		#	self.close_client()

		if not form.validates():
			return render.edit_card(card_id, form, other_tl)
			self.close_client()

		up_card = {
			'title': form.title.value,
			'description': form.description.value,
			'duedate': form.duedate.value
		}

		try:
			self.set_col('cards')
			self.col.update({'_id': ObjectId(card_id)}, {'$set': up_card})
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		raise web.seeother('/board/%s/' % card['board_id'])


class DeleteCard(TCMongoDB):
	@auth
	def GET(self, card_id):
		try:
			# removing card
			self.set_col('cards')
			card = self.col.find_one({'_id': ObjectId(card_id)})
			self.col.remove({'_id': ObjectId(card_id)})

			self.set_col('tasklists')
			self.col.update({'_id': card['tasklist_id']}, {'$pull': {'cards': card['_id']}})
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		raise web.seeother('/board/%s/' % card['board_id'])


class ArchiveCard(TCMongoDB):
	@auth
	def GET(self, card_id):
		try:
			# archiving card
			self.set_col('cards')
			card = self.col.find_one({'_id': ObjectId(card_id)})
			self.col.update({'_id': card['board_id']}, {'$set': {'status': 'status'}})
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		raise web.seeother('/board/%s/' % card['board_id'])


class CardFileUp(TCMongoDB):
	@auth
	def POST(self, card_id):
		inp = web.input(cardfile={})

		if not inp or not inp['cardfile'].value:
			raise web.seeother('/card/%s/edit/' % card_id)

		file_name = inp['cardfile'].filename
		file_value = inp['cardfile'].value

		try:
			self.set_grid()
			self.set_fs()
			new_file_id = self.fs.put(file_value, filename=file_name)
			new_file = self.fs.get(new_file_id)

			self.set_db()
			self.set_col('cards')
			card_file = {'id': new_file._id, 'name': file_name, 'date': new_file.upload_date, 'uploader': current_user('name')}
			self.col.update({'_id': ObjectId(card_id)}, {'$push': {'files': card_file}})

			# return self.fs.get(new_file).read()
		except Exception, e:
			return str(e)
		finally:
			self.close_client()

		raise web.seeother('/card/%s/edit/' % card_id)


class GetFile(TCMongoDB):
	@auth
	def GET(self, card_id, file_id):
		"""
		TODO: stream large files
		"""
		get_file = None
		try:
			self.set_grid()
			self.set_fs()
			get_file = self.fs.get(ObjectId(file_id))
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		if not get_file:
			return render.doh('File not found')

		web.header('Content-type','application/octet-stream')
		web.header('Content-Disposition','attachment; filename=%s' % get_file.filename)

		return  get_file.read()


class DeleteFile(TCMongoDB):
	@auth
	def GET(self, card_id, file_id):
		try:
			self.set_grid()
			self.set_fs()
			self.fs.delete(ObjectId(file_id))

			self.set_col('cards')
			self.col.update({'_id': ObjectId(card_id)}, {'$pull': {'files': {'id': ObjectId(file_id)}}})
		except Exception, e:
			return str(e)
		finally:
			self.close_client()

		raise web.seeother('/card/%s/edit/' % card_id)


class AddComment(TCMongoDB):

	comment_form = wform.Form(
		wform.Textarea('comment', wform.notnull, description='Comment', class_='comment-textarea'),
		wform.Button('add', type='submit', html='Add', description='Add comment', class_='btn')
	)

	@auth
	def GET(self, card_id):
		return render_part.add_comment(card_id, self.comment_form())

	@auth
	def POST(self, card_id):

		form = self.comment_form()
		if not form.validates():
			return render_part.add_comment(card_id, form)

		comment = {
			'_id': ObjectId(),
			'value': form.comment.value,
			'author': current_user('name'),
			'date': datetime.now()
		}

		try:
			self.set_col('cards')
			card = self.col.find_one({'_id': ObjectId(card_id)})
			if not card:
				return 'Unknown card'

			self.col.update({'_id': ObjectId(card_id)}, {'$push': {'comments': comment}})

		except Exception, e:
			form.note = 'Unhandled error : ' + str(e)
			return render_part.add_comment(card_id, form)
		finally:
			self.close_client()

		return render_part.add_comment(card_id, self.comment_form())


class CardComments(TCMongoDB):
	@auth
	def GET(self, card_id):
		try:
			self.set_col('cards')
			card = self.col.find_one({'_id': ObjectId(card_id)}, {'comments': 1})
		except Exception, e:
			return str(e)
		finally:
			self.close_client()

		return render_part.card_comments(card['comments'][::-1])


class MoveCardToList(TCMongoDB):
	@auth
	def GET(self, card_id, tasklist_id):
		try:
			self.set_col('cards')
			card = self.col.find_one({'_id': ObjectId(card_id)})
			previous_tasklist = card['tasklist_id']
			self.col.update({'_id': ObjectId(card_id)}, {'$set': {'tasklist_id': ObjectId(tasklist_id)}})

			self.set_col('tasklists')
			self.col.update({'_id': previous_tasklist}, {'$pull': {'cards': card['_id']}})
			self.col.update({'_id': ObjectId(tasklist_id)}, {'$push': {'cards': card['_id']}})
		except Exception, e:
			return render.doh(str(e))
		finally:
			self.close_client()

		raise web.seeother('/card/%s/edit/' % card_id)


class MoveCardToBoard(TCMongoDB):
	@auth
	def GET(self, card_id, board_id):
		"""
		TODO: move card to board means adding it to a new empty list
		"""

		return 'Soon'

web.wsgi.runwsgi = lambda func, addr=None: web.wsgi.runfcgi(func, addr)

if __name__ == '__main__':
	app.run()