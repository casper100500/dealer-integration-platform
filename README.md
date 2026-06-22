# Dealer Inventory ETL

A backend service for importing, validating, normalizing, and synchronizing vehicle inventory from multiple data sources.

The platform ingests vehicle listings from CSV files and REST APIs provided by different dealerships, validates and transforms incoming data into a unified format, and stores it in a centralized database.

The project demonstrates the implementation of a production-style ETL pipeline using Django, Django REST Framework, Celery, PostgreSQL, and Redis. It includes asynchronous import processing, data validation, duplicate detection, import history tracking, REST APIs, and OpenAPI/Swagger documentation.
