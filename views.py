# -*- coding: utf-8

from django import forms
from django.conf import settings
from django.core.mail import *
from django.db.transaction import commit_on_success
from django.shortcuts import *

from django.contrib.auth.decorators import *
from django.utils.http import urlquote

import codecs
import csv
import datetime

from membership.models import *
from membership.forms import *

def subscription( request ) :
    if request.method == 'POST' :
        form = MembershipInfoForm(request.POST)
        if form.is_valid() :
            form.save()
            msg_subj = "Demande d'adhésion"
            msg_txt = """Bonjour,

Une demande d'adhésion vient d'être postée sur le site. Pour la modérer :
    %s
""" % ("http://jebif.fr/%smembership/admin/subscription/" % settings.ROOT_URL)
            send_mail(settings.EMAIL_SUBJECT_PREFIX + msg_subj, msg_txt, 
                        settings.SERVER_EMAIL, [a[1] for a in settings.MEMBERSHIP_MANAGERS],
                        fail_silently=True)
            return HttpResponseRedirect("ok/")
    else :
        form = MembershipInfoForm()

    return render(request, "membership/subscription.html", {"form": form}) 

@login_required
def subscription_renew( request, info_id ) :
    info = MembershipInfo.objects.get(id=info_id)

    if info.user != request.user :
        path = urlquote(request.get_full_path())
        from django.contrib.auth import REDIRECT_FIELD_NAME
        tup = settings.LOGIN_URL, REDIRECT_FIELD_NAME, path
        return HttpResponseRedirect('%s?%s=%s' % tup)

    membership = info.latter_membership()

    today = datetime.date.today()

    if membership.date_begin >= today :
                return render(request, "membership/subscription_renewed.html", "membership": membership})

    if request.method == 'POST' :
        form = MembershipInfoForm(request.POST, instance=info)
        if form.is_valid() :
            form.save()
            m = Membership(info=info)
            if membership.has_expired() :
                m.init_date(today)
                info.inscription_date = today
                info.active = True
                info.save()
            else :
                m.init_date(membership.date_end + datetime.timedelta(1))
            m.save()
                        return render(request, "membership/subscription_renew.html", {"membership": m})
    else :
        form = MembershipInfoForm(instance=info)

        context = { "form": form,
                    "membership": membership,
                    "today": today,
                  }
        return render(request, "membership/subscription_renew.html", context)

@login_required
def subscription_self_update( request ) :
    info = MembershipInfo.objects.get(user=request.user)
    return subscription_update(request, info.id)

@login_required
def subscription_update( request, info_id ) :
    info = MembershipInfo.objects.get(id=info_id)
    if info.user != request.user :
        path = urlquote(request.get_full_path())
        from django.contrib.auth import REDIRECT_FIELD_NAME
        tup = settings.LOGIN_URL, REDIRECT_FIELD_NAME, path
        return HttpResponseRedirect('%s?%s=%s' % tup)

    membership = info.latter_membership()

    if membership.has_expired() :
        return subscription_renew(request, info_id)

    old_email = info.email

    if request.method == 'POST' :
        form = MembershipInfoForm(request.POST, instance=info)
        if form.is_valid() :
            info = form.save()
            if info.user is not None :
                u = info.user
                if u.email != info.email :
                    u.email = info.email
                    u.save()
            if info.email != old_email :
                MembershipInfoEmailChange.objects.create(old_email=old_email, info=info)
                        return render(request, "membership/subscription_updated.html", {"membership": membership})
    else :
        form = MembershipInfoForm(instance=info)

        context = { "form": form,
                    "membership": membership,
                  }
        return render(request, "membership/subscription_update.html", context)


def subscription_preupdate( request ) :

    class MembershipInfoEmailForm( forms.Form ) :
        email = forms.EmailField(required=True)

        def clean_email( self ) :
            data = self.cleaned_data["email"]
            try :
                info = MembershipInfo.objects.get(email=data)
            except MembershipInfo.DoesNotExist :
                raise forms.ValidationError(u"E-mail inconnu")
            return info
    
    if request.method == "POST" :
        form = MembershipInfoEmailForm(request.POST)
        if form.is_valid() :
            info = form.cleaned_data["email"]
            data = info.get_contact_data()
            msg_from = "NO-REPLY@jebif.fr"
            msg_to = [info.email]
            msg_subj = u"Ton adhésion à JeBiF"
            msg_txt = u"""
Bonjour %(firstname)s,

Tu peux modifier ton adhésion à l'association JeBiF en te rendant sur
    %(url_update)s
avec ton identifiant '%(login)s'%(passwd_setup)s.

À bientôt,
L’équipe du RSG-France (JeBiF)
        """ % data
            send_mail(msg_subj, msg_txt, msg_from, msg_to)
                        return render(request, "membership/subscription_preupdated.html", {"email": info.email})
    else :
        form = MembershipInfoEmailForm()
        return render(request, "membership/subscription_preupdate.html", {"form": form})


def is_admin() :
    def validate( u ) :
        return u.is_authenticated() and u.is_staff
    return user_passes_test(validate)

@is_admin()
def admin_subscription( request ) :
    infos = MembershipInfo.objects.filter(active=False, deleted=False, membership=None)
    return render(request, "membership/admin_subscription.html", {"infos": infos})

@is_admin()
def admin_subscription_accept( request, info_id ) :
    with commit_on_success() :
        info = MembershipInfo.objects.get(id=info_id)
        info.active = True
        info.inscription_date = datetime.date.today()
        m = Membership(info=info)
        m.init_date(info.inscription_date)
        m.save()
        info.save()

    msg_from = "NO-REPLY@jebif.fr"
    msg_to = [info.email]
    msg_subj = "Bienvenue dans l'association JeBiF"
    msg_txt = u"""
Bonjour %s,

Nous avons bien pris en compte ton adhésion à l’association JeBiF. N’hésite pas à nous contacter si tu as des questions, des commentaires, des idées, etc…

Tu connais sans doute déjà notre site internet http://jebif.fr. Tu peux aussi faire un tour sur notre page internationale du RSG-France.
http://www.iscbsc.org/rsg/rsg-france

Tu vas être inscrit à la liste de discussion des membres de l’association. Tu pourras y consulter les archives si tu le souhaites.
http://lists.jebif.fr/mailman/listinfo/membres

À bientôt,
L’équipe du RSG-France (JeBiF)
""" % info.firstname
    send_mail(msg_subj, msg_txt, msg_from, msg_to)

    return HttpResponseRedirect("../../")

@is_admin()
def admin_subscription_reject( request, info_id ) :
    info = get_object_or_404(MembershipInfo, id=info_id)
    info.deleted = True
    info.save()
    return HttpResponseRedirect("../../")

@is_admin()
def admin_export_csv( request ) :
    charset = 'utf-8'
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=membres_jebif.csv'

    writer = csv.writer(response)
    writer.writerow(['Nom', 'Prénom', 'E-mail',
        'Laboratoire', 'Ville', 'Pays', 'Poste actuel',
        'Motivation', 'Date inscription'])

    infos = MembershipInfo.objects.filter(active=True).extra(select={'ord':'lower(lastname)'}).order_by('ord')
    e = lambda s : s.encode(charset)
    for i in infos :
        writer.writerow(map(e, [i.lastname, i.firstname, 
            i.email, i.laboratory_name, i.laboratory_city,
            i.laboratory_country, i.position,
            i.motivation.replace("\r\n", " -- "),
            i.inscription_date.isoformat()]))

    return response


