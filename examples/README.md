# Vehicle import examples

These CSV files are sample vehicle feeds for testing the importer.

- `vehicle_import_standard_fields.csv` uses the built-in standard field names.
- `vehicle_import_custom_fields_extra_columns.csv` uses nonstandard source columns and extra columns for parsing config tests.
- `vehicle_import_dealer_northside.csv`, `vehicle_import_dealer_lakeside.csv`, and `vehicle_import_dealer_downtown.csv` are intended to be imported as separate dealer feeds. Some VINs repeat across these files so importer behavior can be checked for one vehicle listed by multiple dealers.
- `vehicle_import_large_2,5k_records.csv` contains 2,500 rows with deterministic randomized VINs.

Dealer identity is not stored in these CSVs. Select the dealer on the `VehicleDataImport` record before processing the file.
