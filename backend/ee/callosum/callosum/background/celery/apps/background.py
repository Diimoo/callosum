from callosum.background.celery.apps.background import celery_app


celery_app.autodiscover_tasks(
    [
        "ee.callosum.background.celery.tasks.doc_permission_syncing",
        "ee.callosum.background.celery.tasks.external_group_syncing",
        "ee.callosum.background.celery.tasks.cleanup",
        "ee.callosum.background.celery.tasks.tenant_provisioning",
        "ee.callosum.background.celery.tasks.query_history",
    ]
)
