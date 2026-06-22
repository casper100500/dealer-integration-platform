from __future__ import annotations

from .models import ImportSource, VehicaleDataImport
from .vehicle_loaders import VehicleBaseLoader, VehicleDjangoLoader


def task_run_vehicle_data_import(data_import_id: int) -> None:
    """Select and run the loader for a vehicle data import."""
    data_import = VehicaleDataImport.objects.get(pk=data_import_id)
    loader_class: type[VehicleBaseLoader] = VehicleBaseLoader

    if data_import.source == ImportSource.django:
        loader_class = VehicleDjangoLoader

    loader_class(data_import).run()
