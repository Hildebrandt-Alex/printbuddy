from django.urls import path

from . import views

app_name = "studio"

urlpatterns = [
    path("",                              views.dashboard,           name="dashboard"),
    path("jobs/",                         views.job_list,            name="job_list"),
    path("jobs/create/",                  views.job_create,          name="job_create"),
    path("jobs/<uuid:job_id>/",           views.job_detail,          name="job_detail"),
    path("jobs/<uuid:job_id>/status/",    views.job_status_partial,  name="job_status"),
    path("jobs/<uuid:job_id>/results/",   views.job_results,         name="job_results"),
    path("jobs/<uuid:job_id>/select/",    views.asset_select,        name="asset_select"),
    path("prompts/",                      views.prompt_library,      name="prompt_library"),
]
