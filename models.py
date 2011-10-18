# -*- coding: utf-8 -*-

import datetime

from django.conf import settings
from django.db import models
from django.db import IntegrityError
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify

VERSION = 2

class MembershipInfo( models.Model ) :
	user = models.ForeignKey(User, blank=True, null=True)
	email = models.EmailField(unique=True)
	firstname = models.CharField("Prénom", max_length=75)
	lastname = models.CharField("Nom", max_length=75)
	laboratory_name = models.CharField("Laboratoire", max_length=75)
	laboratory_city = models.CharField("Ville", max_length=75)
	laboratory_cp = models.CharField("Code Postal", max_length=7)
	laboratory_country = models.CharField("Pays", max_length=75)
	position = models.CharField("Poste actuel", max_length=75)
	motivation = models.TextField("Motivation pour adhérer", blank=True)

	inscription_date = models.DateField(default=datetime.date.today)
	active = models.BooleanField(default=False)
	deleted = models.BooleanField(default=False)

	def latter_membership( self ) :
		try :
			return Membership.objects.filter(info=self).order_by("-date_begin")[0]
		except IndexError :
			print(u"No membership for %s !" % self)
			raise

	def get_contact_data( self ) :
		def ensure_ROOT( url ) :
			if url[1:].startswith(settings.ROOT_URL) :
				return url
			else :
				return "/%s%s" % (settings.ROOT_URL, url[1:])
		from jebif.membership.views import subscription_renew, subscription_update
		url_renew = ensure_ROOT(reverse(subscription_renew, kwargs={"info_id": self.id}))
		url_update = ensure_ROOT(reverse(subscription_update, kwargs={"info_id": self.id}))
		new_passwd = self.make_user()
		return {
			"firstname" : self.firstname,
			"url_renew" : "%s%s" % (settings.HTTP_DOMAIN, url_renew),
			"url_update" : "%s%s" % (settings.HTTP_DOMAIN, url_update),
			"login" : self.user.username,
			"passwd_setup" : " et ton mot de passe '%s'" % new_passwd if new_passwd is not None 
								else ""
		}

	def make_user( self ) :
		if self.user is not None :
			return None
		# 1. try to find a User matching email
		matching = User.objects.filter(email=self.email, is_active=True)
		if matching :
			self.user = matching[0]
			if len(matching) > 1 :
				matching2 = matching.filter(is_staff=False)
				if matching2 :
					self.user = matching2[0]
			self.save()
			return None
		else :
			passwd = User.objects.make_random_password(8)
			base_login = slugify(self.firstname)[0] + \
							slugify(self.lastname)[:7]
			login = base_login
			salt = 2
			created = False
			while not created :
				try :
					self.user = User.objects.create_user(login, self.email, passwd)
					created = True
				except IntegrityError :
					login = base_login + "%d" % salt
					salt += 1
			self.save()
			return passwd

	def __unicode__( self ) :
		return "%s %s <%s>%s" % (self.firstname, self.lastname,
								self.email, "" if self.active else " (inactive)")
	class Meta :
		verbose_name = "membre"


def end_membership(base=None) :
	d = base
	if d is None :
		d = datetime.date.today()
	try :
		end = datetime.date(d.year+1,d.month,d.day)
	except ValueError :
		end = datetime.date(d.year+1,d.month,d.day-1)
	return end - datetime.timedelta(1)


class Membership( models.Model ) :
	info = models.ForeignKey(MembershipInfo)
	date_begin = models.DateField()
	date_end = models.DateField(default=end_membership)

	def init_date( self, date_begin ) :
		self.date_begin = date_begin
		self.date_end = end_membership(self.date_begin)
	
	def has_expired( self ) :
		return self.date_end < datetime.date.today()
	
	def expire_delta( self ) :
		return self.date_end - datetime.date.today() + datetime.timedelta(1)

	@classmethod
	def current_objects( celf ) :
		today = datetime.date.today
		return celf.objects.filter(info__active=True,
					date_begin__lte=today, date_end__gt=today)

	def __unicode__( self ) :
		return u"%s/%s %s" % (self.date_begin, self.date_end, self.info)

class MembershipInfoEmailChange( models.Model ) :
	date = models.DateField(default=datetime.date.today)
	info = models.ForeignKey(MembershipInfo)
	old_email = models.EmailField()

class DatabaseInfo( models.Model ) : 
	""" 
	Version de la structure de la base de données.
	Utilisé pour migrer les données.
	"""
	version = models.SmallIntegerField()

	@classmethod
	def instance( celf ) : 
		try :
			return celf.objects.all()[0]
		except IndexError :
			celf.objects.create(version=0)
			return celf.objects.all()[0]

