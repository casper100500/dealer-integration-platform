from inventory.models import Vehicle


deleted_count, deleted_by_model = Vehicle.objects.all().delete()

print(
    f"Deleted vehicles: {deleted_by_model.get('inventory.Vehicle', 0)} "
    f"vehicle rows, {deleted_count} total rows."
)
