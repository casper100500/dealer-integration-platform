from __future__ import annotations

from config.celery import app as celery

from .models import ImportSource, VehicleDataImport
from .vehicle_loaders import (
    VehicleBaseLoader,
    VehicleDjangoLoader,
    VehicleUSACarLoader,
)


@celery.task
def task_run_vehicle_data_import(data_import_id: int) -> None:
    """Select and run the loader for a vehicle data import."""
    data_import = VehicleDataImport.objects.get(pk=data_import_id)
    loader_class: type[VehicleBaseLoader] = VehicleBaseLoader

    if data_import.source == ImportSource.django:
        loader_class = VehicleDjangoLoader
    elif data_import.source == ImportSource.usacar:
        loader_class = VehicleUSACarLoader

    loader_class(data_import).run_parser()
