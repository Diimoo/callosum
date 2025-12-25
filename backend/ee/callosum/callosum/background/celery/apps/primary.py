from callosum.background.celery.apps.primary import celery_app


celery_app.autodiscover_tasks(
    [
        "ee.callosum.background.celery.tasks.doc_permission_syncing",
        "ee.callosum.background.celery.tasks.external_group_syncing",
        "ee.callosum.background.celery.tasks.cloud",
        "ee.callosum.background.celery.tasks.ttl_management",
        "ee.callosum.background.celery.tasks.usage_reporting",
    ]
)
