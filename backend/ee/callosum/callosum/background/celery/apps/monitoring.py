from callosum.background.celery.apps.monitoring import celery_app

celery_app.autodiscover_tasks(
    [
        "ee.callosum.background.celery.tasks.tenant_provisioning",
    ]
)
