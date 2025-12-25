from callosum.background.celery.apps.light import celery_app

celery_app.autodiscover_tasks(
    [
        "ee.callosum.background.celery.tasks.doc_permission_syncing",
        "ee.callosum.background.celery.tasks.external_group_syncing",
    ]
)
