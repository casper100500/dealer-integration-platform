# Vehicle import examples

The examples are grouped by import source:

- `csv/` contains standard and custom CSV feeds for Django-admin imports.
- `usa_car/inventory_response.json` contains the fictional raw USA Car API
  response used by integration tests.
- `usa_car/vehicle_import.csv` contains the provider-specific CSV produced from
  that response.

The dealer CSV files under `csv/` represent separate dealer feeds. Some VINs
repeat intentionally so one vehicle can be tested with offers from multiple
dealers. The large example contains 2,500 deterministic records.

Dealer identity is not stored in the files. Select the dealer on the
`VehicleDataImport` record before processing an uploaded CSV.

To test USA Car parsing manually in Django admin:

1. Upload `usa_car/vehicle_import.csv` as a `File`.
2. Create a `VehicleDataImport` for the desired dealer.
3. Select `USA car` as the source and choose the uploaded file.
4. Save the import so its normal signal and Celery task process the CSV.
