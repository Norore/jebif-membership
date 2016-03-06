
from django.conf.urls import *
from django.views.generic import TemplateView
#from jebif.membership.views import *
from membership import views

urlpatterns = patterns('',
	('^subscription/$', views.subscription),
	#('^subscription/ok/$', TemplateViews.as_view(template="membership/subscription-ok.html")),
        ('^subscription/ok/$', TemplateView.as_view(template_name = "membership/subscription-ok.html")),
	('^subscription/(?P<info_id>\d+)/renew/$', views.subscription_renew),
	('^subscription/(?P<info_id>\d+)/update/$', views.subscription_update),
	('^subscription/me/update/$', views.subscription_self_update),
	('^subscription/update/$', views.subscription_preupdate),
	('^admin/export/csv/$', views.admin_export_csv),
	('^admin/subscription/$', views.admin_subscription),
	('^admin/subscription/accept/(?P<info_id>\d+)/$', views.admin_subscription_accept),
	('^admin/subscription/reject/(?P<info_id>\d+)/$', views.admin_subscription_reject)
)

