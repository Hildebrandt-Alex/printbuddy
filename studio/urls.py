from django.urls import path

from . import views

app_name = "studio"

urlpatterns = [
    path("",                              views.dashboard,           name="dashboard"),
    path("jobs/",                         views.job_list,            name="job_list"),
    path("jobs/<uuid:job_id>/",           views.job_detail,          name="job_detail"),
    path("jobs/<uuid:job_id>/status/",    views.job_status_partial,  name="job_status"),
    path("jobs/<uuid:job_id>/results/",   views.job_results,         name="job_results"),
    path("jobs/<uuid:job_id>/select/",    views.asset_select,        name="asset_select"),
    path("prompts/",                      views.prompt_library,      name="prompt_library"),
    
    # Knowledge Base
    path("knowledge/models/",             views.knowledge_models,    name="knowledge_models"),
    path("knowledge/it/",                 views.knowledge_it,        name="knowledge_it"),

    # Guided Wizard (Haupteinstieg)
    path("create/",          views.wizard_step1,   name="wizard_step1"),
    path("create/step2/",    views.wizard_step2,   name="wizard_step2"),
    path("create/step3/",    views.wizard_step3,   name="wizard_step3"),
    path("create/confirm/",  views.wizard_confirm, name="wizard_confirm"),

    # Experten-Modus (versteckt, direkt erreichbar)
    path("jobs/create/",     views.job_create,     name="job_create"),
]
