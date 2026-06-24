import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0003_inventorylisting"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="InventoryListing",
            new_name="DealerOffer",
        ),
        migrations.AlterField(
            model_name="dealeroffer",
            name="dealer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="dealer_offers",
                to="inventory.dealer",
            ),
        ),
        migrations.AlterField(
            model_name="dealeroffer",
            name="vehicle",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="dealer_offers",
                to="inventory.vehicle",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="dealeroffer",
            name="unique_dealer_vehicle_listing",
        ),
        migrations.AddConstraint(
            model_name="dealeroffer",
            constraint=models.UniqueConstraint(
                fields=("dealer", "vehicle"),
                name="unique_dealer_vehicle_offer",
            ),
        ),
        migrations.RemoveIndex(
            model_name="dealeroffer",
            name="inventory_i_dealer__fa5874_idx",
        ),
        migrations.AddIndex(
            model_name="dealeroffer",
            index=models.Index(
                fields=["dealer", "vehicle"],
                name="inventory_d_dealer__791d69_idx",
            ),
        ),
    ]
